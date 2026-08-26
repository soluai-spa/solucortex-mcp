"""SoluCortex MCP server — living technical memory for AI agents.

Wraps the SoluCortex REST API and exposes it to any MCP client (Claude Code, Claude
Desktop, Cursor, Codex, Cline, ...) as tools: recall context at the start of a task and
record memories when it closes. The client acts as an *authorized agent* (Bearer api_key),
so memories it creates are stored approved and traced automatically.

Transports:
  stdio (default)  Local single-tenant mode. Credentials come from the environment:
    SOLUCORTEX_URL         Base URL. Default: https://solucortex.ai
    SOLUCORTEX_API_KEY     Project API key (prefix scx_). REQUIRED.
    SOLUCORTEX_PROJECT_ID  Default project UUID. Can be overridden per call.
  http (MCP_TRANSPORT=http or --http)  Remote multi-tenant mode (Streamable HTTP,
    stateless) listening on $PORT (default 8080). Credentials travel with EACH request:
    'Authorization: Bearer <api key>' and optional 'X-Solucortex-Project: <uuid>'.
    Environment credentials are ignored in this mode. See http_app.py.

Never hardcode the API key: it is read from the environment (stdio) or the request (http).
"""

from __future__ import annotations

import contextvars
import os
import sys
from typing import Annotated, Any

import httpx
from mcp.server.fastmcp import FastMCP
from pydantic import Field

DEFAULT_URL = "https://solucortex.ai"
NORMAL_TIMEOUT = 30.0
# Endpoints backed by OpenAI embeddings have a reduced rate limit (20 req/min) and are slower.
OPENAI_TIMEOUT = 60.0

mcp = FastMCP("solucortex")


# --- Credential resolution ---------------------------------------------------
# stdio mode (default): credentials come from the environment, set by the client config
# or run.sh. http mode (remote, multi-tenant): credentials travel with each request and
# are stashed in these context variables by the middleware in http_app.py; the
# environment is ignored so one tenant can never inherit another tenant's credentials.

_http_mode = False

_request_api_key: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "solucortex_request_api_key", default=None
)
_request_project_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "solucortex_request_project_id", default=None
)


def enable_http_mode() -> None:
    global _http_mode
    _http_mode = True


def _base_url() -> str:
    return os.environ.get("SOLUCORTEX_URL", DEFAULT_URL).rstrip("/")


def _api_key() -> str | None:
    if _http_mode:
        return _request_api_key.get()
    return os.environ.get("SOLUCORTEX_API_KEY")


def _resolve_project_id(project_id: str | None) -> str | None:
    if project_id:
        return project_id
    if _http_mode:
        return _request_project_id.get()
    return os.environ.get("SOLUCORTEX_PROJECT_ID")


def _missing_project_error() -> dict[str, Any]:
    if _http_mode:
        return {
            "ok": False,
            "error": "Missing project_id: pass it as an argument or send the "
            "X-Solucortex-Project header with your default project UUID.",
        }
    return {"ok": False, "error": "Missing project_id (neither argument nor SOLUCORTEX_PROJECT_ID)."}


def _config_error() -> str | None:
    """Return an actionable message if configuration is missing, else None."""
    if _api_key():
        return None
    if _http_mode:
        return (
            "Missing API key. Send your SoluCortex project API key on every request as "
            "'Authorization: Bearer <api key>'."
        )
    return (
        "Missing SOLUCORTEX_API_KEY. Set it in the MCP server environment with your "
        "project API key (prefix scx_). Without it, memory cannot be read or written."
    )


async def _request(
    method: str,
    path: str,
    *,
    json_body: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    timeout: float = NORMAL_TIMEOUT,
) -> dict[str, Any]:
    """Call the SoluCortex API and return a {ok, ...} dict that is easy for a model to interpret."""
    cfg = _config_error()
    if cfg:
        return {"ok": False, "error": cfg}

    url = f"{_base_url()}/api/v1{path}"
    headers = {
        "Authorization": f"Bearer {_api_key()}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.request(
                method, url, headers=headers, json=json_body, params=params
            )
    except httpx.TimeoutException:
        return {"ok": False, "error": f"Timeout calling {method} {path} (>{timeout}s)."}
    except httpx.HTTPError as exc:
        return {"ok": False, "error": f"Network error calling {method} {path}: {exc}"}

    try:
        payload: Any = resp.json()
    except ValueError:
        payload = resp.text

    if resp.is_success:
        return {"ok": True, "status": resp.status_code, "data": payload}

    hint = ""
    if resp.status_code == 401:
        hint = " (Invalid or missing API key: check SOLUCORTEX_API_KEY.)"
    elif resp.status_code == 403:
        hint = " (No access to this project: ensure the API key matches project_id.)"
    elif resp.status_code == 422:
        hint = (
            " (Validation failed: check 'type' against the values your backend accepts, "
            "and that title/content/importance are valid.)"
        )
    elif resp.status_code == 429:
        hint = " (Rate limit: OpenAI-backed endpoints allow 20 req/min; normal ones 120 req/min.)"
    return {
        "ok": False,
        "status": resp.status_code,
        "error": f"HTTP {resp.status_code} on {method} {path}.{hint}",
        "data": payload,
    }


@mcp.tool(
    annotations={
        "title": "SoluCortex: recall task context",
        "readOnlyHint": True,
        "openWorldHint": True,
    }
)
async def solucortex_recall(
    query: Annotated[
        str,
        Field(description="Describe the current task/module in natural language, e.g. "
              "'implement API key rotation in the secrets module'. Used to semantically "
              "retrieve the most relevant memories."),
    ],
    project_id: Annotated[
        str | None,
        Field(description="Project UUID. If omitted, uses SOLUCORTEX_PROJECT_ID."),
    ] = None,
) -> dict[str, Any]:
    """Build living context for a task (POST /context/build).

    Call this at the START of a task, before touching code: returns approved, active
    memories (decisions, conventions, risks, sensitive modules, architecture) ranked by
    semantic similarity + importance. Uses OpenAI embeddings (slower, 20 req/min)."""
    pid = _resolve_project_id(project_id)
    if not pid:
        return _missing_project_error()
    return await _request(
        "POST", "/context/build",
        json_body={"project_id": pid, "query": query},
        timeout=OPENAI_TIMEOUT,
    )


@mcp.tool(
    annotations={
        "title": "SoluCortex: semantic memory search",
        "readOnlyHint": True,
        "openWorldHint": True,
    }
)
async def solucortex_search(
    query: Annotated[str, Field(description="Question or topic to search across the project's memories.")],
    limit: Annotated[int, Field(description="Max memories to return.", ge=1, le=50)] = 10,
    project_id: Annotated[
        str | None, Field(description="Project UUID. If omitted, uses SOLUCORTEX_PROJECT_ID.")
    ] = None,
) -> dict[str, Any]:
    """Ad-hoc semantic search of memories (POST /search/semantic).

    Use for specific questions during a task (e.g. 'how is authentication implemented?'),
    distinct from recall which builds the full startup context. Uses OpenAI embeddings
    (20 req/min)."""
    pid = _resolve_project_id(project_id)
    if not pid:
        return _missing_project_error()
    return await _request(
        "POST", "/search/semantic",
        json_body={"project_id": pid, "query": query, "limit": limit},
        timeout=OPENAI_TIMEOUT,
    )


@mcp.tool(
    annotations={
        "title": "SoluCortex: record a memory",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    }
)
async def solucortex_remember(
    type: Annotated[
        str,
        Field(description="Memory type. The backend validates the value. Canonical vocabulary: "
              "architecture, decision, risk, convention, bug_history, tech_debt, sensitive_module, "
              "learning, external_integration. (Older backends may use technical_decision, "
              "historical_bug, current_state, task_closure.) On HTTP 422, retry with the "
              "alternate vocabulary."),
    ],
    title: Annotated[str, Field(description="Short, clear title (~80 chars max).", max_length=120)],
    content: Annotated[
        str,
        Field(description="Full content: what to remember, why it matters, where it applies and what "
              "it prevents. NEVER include real secrets (tokens, passwords, .env, credentials)."),
    ],
    importance: Annotated[
        int,
        Field(description="Priority 1-10. Default 5. 6-7 high; 8-9 important decision/risk/convention; "
              "10 critical.", ge=1, le=10),
    ] = 5,
    project_id: Annotated[
        str | None, Field(description="Project UUID. If omitted, uses SOLUCORTEX_PROJECT_ID.")
    ] = None,
) -> dict[str, Any]:
    """Record a memory in SoluCortex (POST /memories).

    Call when closing a task or making a relevant technical decision. As an authorized
    agent (Bearer api_key), the memory is stored with status 'approved' and traced. Never
    store real secrets: if you find one, record location/type/severity and action taken,
    with a redacted reference."""
    pid = _resolve_project_id(project_id)
    if not pid:
        return _missing_project_error()
    return await _request(
        "POST", "/memories",
        json_body={
            "project_id": pid,
            "type": type,
            "title": title,
            "content": content,
            "importance": importance,
        },
    )


@mcp.tool(
    annotations={
        "title": "SoluCortex: list memories",
        "readOnlyHint": True,
        "openWorldHint": True,
    }
)
async def solucortex_list_memories(
    limit: Annotated[int, Field(description="Max memories to return.", ge=1, le=100)] = 20,
    project_id: Annotated[
        str | None, Field(description="Project UUID. If omitted, uses SOLUCORTEX_PROJECT_ID.")
    ] = None,
) -> dict[str, Any]:
    """List the project's memories without semantic search (GET /memories).

    Useful for quick inspection/audit or to confirm a just-created memory was stored.
    Does not consume OpenAI quota."""
    pid = _resolve_project_id(project_id)
    params: dict[str, Any] = {"limit": limit}
    if pid:
        params["project_id"] = pid
    return await _request("GET", "/memories", params=params)


def main() -> None:
    """Console entry point: stdio by default; MCP_TRANSPORT=http or --http for remote mode."""
    transport = os.environ.get("MCP_TRANSPORT", "stdio").strip().lower()
    if "--http" in sys.argv[1:]:
        transport = "http"
    if transport in {"http", "streamable-http", "streamable_http"}:
        import uvicorn

        from .http_app import build_http_app

        uvicorn.run(build_http_app(), host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
    else:
        mcp.run()


if __name__ == "__main__":
    main()
