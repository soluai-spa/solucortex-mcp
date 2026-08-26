"""Remote (Streamable HTTP) mode for the SoluCortex MCP server — multi-tenant.

Public deployment model (mcp.solucortex.ai on Cloud Run): one shared server, zero stored
tenant credentials. Every request must carry the caller's own SoluCortex project API key:

    Authorization: Bearer <project API key>
    X-Solucortex-Project: <project UUID>        (optional default project_id)

The middleware rejects unauthenticated MCP requests with 401, stashes the request's
credentials in context variables (read by server._api_key / server._resolve_project_id),
and exposes GET /healthz without auth for Cloud Run health checks. The MCP endpoint runs
stateless: no session state survives between requests, so tenants share nothing.
"""

from __future__ import annotations

import json
from typing import Any

from starlette.datastructures import Headers
from starlette.types import ASGIApp, Receive, Scope, Send

from . import server

HEALTH_PATHS = {"/healthz", "/healthz/"}
PROJECT_HEADER = "x-solucortex-project"


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
    """Pure ASGI middleware: health bypass, 401 without a Bearer key, per-request credentials.

    Context variables set here propagate into the MCP request-handling task because the
    stateless session manager spawns it from the request's own context. Never log the key.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        if scope.get("path", "") in HEALTH_PATHS:
            await _send_json(send, 200, {"status": "ok", "service": "solucortex-mcp"})
            return

        headers = Headers(scope=scope)
        auth = headers.get("authorization", "")
        api_key = auth[7:].strip() if auth[:7].lower() == "bearer " else ""
        if not api_key:
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
            return

        key_token = server._request_api_key.set(api_key)
        pid_token = server._request_project_id.set(headers.get(PROJECT_HEADER) or None)
        try:
            await self.app(scope, receive, send)
        finally:
            server._request_api_key.reset(key_token)
            server._request_project_id.reset(pid_token)


def build_http_app() -> ASGIApp:
    """Build the ASGI app for the remote mode (MCP endpoint at /mcp, health at /healthz)."""
    server.enable_http_mode()
    # Stateless is required for multi-tenancy: a persistent session task would be created
    # under the first caller's context and serve later callers with the wrong credentials.
    server.mcp.settings.stateless_http = True
    return CredentialsMiddleware(server.mcp.streamable_http_app())
