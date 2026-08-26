"""Remote (Streamable HTTP) mode for the SoluCortex MCP server — multi-tenant.

Public deployment model (mcp.solucortex.ai on Cloud Run): one shared server, zero stored
tenant credentials. Every request must carry the caller's own SoluCortex project API key:

    Authorization: Bearer <project API key>
    X-Solucortex-Project: <project UUID>        (optional default project_id)

The middleware rejects unauthenticated MCP requests with 401, oversized bodies with 413,
stashes the request's credentials in context variables (read by server._api_key /
server._resolve_project_id), and exposes GET /health (and /healthz) without auth. The MCP
endpoint runs stateless: no session state survives between requests, so tenants share
nothing. Every request emits one structured JSON access log line; the API key itself never
appears in logs — only its SHA-256 fingerprint.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from mcp.server.transport_security import TransportSecuritySettings
from starlette.datastructures import Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from . import server
from .server import _key_fingerprint

# /health is the public path: Google's frontend intercepts /healthz on Cloud Run and
# answers its own 404 before the request reaches the container. /healthz kept for local use.
HEALTH_PATHS = {"/health", "/health/", "/healthz", "/healthz/"}
PROJECT_HEADER = "x-solucortex-project"

# MCP tool calls are small JSON-RPC payloads; anything near this size is abuse.
MAX_BODY_BYTES = 1_000_000

access_log = logging.getLogger("solucortex_mcp.access")


async def _send_json(
    send: Send,
    status: int,
    payload: dict[str, Any],
    extra_headers: list[tuple[bytes, bytes]] | None = None,
) -> None:
    body = json.dumps(payload).encode()
    headers = [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(body)).encode()),
        *(extra_headers or []),
    ]
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": body})


class CredentialsMiddleware:
    """Pure ASGI middleware: health bypass, 401 without a Bearer key, 413 over the body
    limit, per-request credentials, and one JSON access-log line per request.

    Context variables set here propagate into the MCP request-handling task because the
    stateless session manager spawns it from the request's own context. Never log the key.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        started = time.monotonic()
        status_holder = {"status": 0}
        client = scope.get("client") or ("-", 0)
        headers = Headers(scope=scope)
        auth = headers.get("authorization", "")
        api_key = auth[7:].strip() if auth[:7].lower() == "bearer " else ""

        def _log(extra: dict[str, Any] | None = None) -> None:
            fields: dict[str, Any] = {
                "type": "access",
                "method": scope.get("method", "-"),
                "path": scope.get("path", "-"),
                "status": status_holder["status"],
                "dur_ms": round((time.monotonic() - started) * 1000, 1),
                "client_ip": client[0],
                "key_fp": _key_fingerprint(api_key) if api_key else "-",
                "project_header": bool(headers.get(PROJECT_HEADER)),
            }
            if extra:
                fields.update(extra)
            access_log.info(json.dumps(fields))

        async def counting_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                status_holder["status"] = message["status"]
            await send(message)

        if scope.get("path", "") in HEALTH_PATHS:
            status_holder["status"] = 200
            await _send_json(send, 200, {"status": "ok", "service": "solucortex-mcp"})
            return  # health checks are not logged: they would dominate the log volume

        try:
            content_length = int(headers.get("content-length", "0") or "0")
        except ValueError:
            content_length = 0
        if content_length > MAX_BODY_BYTES:
            status_holder["status"] = 413
            await _send_json(
                send, 413, {"error": f"Payload too large (max {MAX_BODY_BYTES} bytes)."}
            )
            _log({"reason": "payload_too_large", "content_length": content_length})
            return

        if not api_key:
            status_holder["status"] = 401
            await _send_json(
                send,
                401,
                {
                    "error": "Missing API key. Send your SoluCortex project API key as "
                    "'Authorization: Bearer <api key>' on every request. Get one at "
                    "https://solucortex.ai."
                },
                extra_headers=[(b"www-authenticate", b"Bearer")],
            )
            _log({"reason": "missing_api_key"})
            return

        key_token = server._request_api_key.set(api_key)
        pid_token = server._request_project_id.set(headers.get(PROJECT_HEADER) or None)
        try:
            await self.app(scope, receive, counting_send)
        finally:
            server._request_api_key.reset(key_token)
            server._request_project_id.reset(pid_token)
            _log()


def build_http_app() -> ASGIApp:
    """Build the ASGI app for the remote mode (MCP endpoint at /mcp, health at /health)."""
    server.enable_http_mode()
    # Stateless is required for multi-tenancy: a persistent session task would be created
    # under the first caller's context and serve later callers with the wrong credentials.
    server.mcp.settings.stateless_http = True
    # DNS-rebinding protection is meant for localhost servers; newer SDKs enable it with a
    # localhost allowlist, which 421-rejects public Hosts (*.run.app, mcp.solucortex.ai).
    # This is a public service: auth is the per-request Bearer key, not the Host header.
    server.mcp.settings.transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=False
    )
    return CredentialsMiddleware(server.mcp.streamable_http_app())
