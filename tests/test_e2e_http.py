"""End-to-end: real uvicorn server + real MCP client over Streamable HTTP.

Proves the multi-tenant contract of SCX-MCP-08: each request's Authorization /
X-Solucortex-Project headers reach the SoluCortex backend call, environment
credentials are ignored, and two clients with different keys don't leak into
each other.
"""

import httpx
import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

EXPECTED_TOOLS = {
    "solucortex_recall",
    "solucortex_search",
    "solucortex_remember",
    "solucortex_update_memory",
    "solucortex_flag_memory",
    "solucortex_list_memories",
}


async def _call_list_memories(url: str, api_key: str, project: str) -> None:
    async with streamablehttp_client(
        f"{url}/mcp",
        headers={"Authorization": f"Bearer {api_key}", "X-Solucortex-Project": project},
    ) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            assert {t.name for t in tools.tools} == EXPECTED_TOOLS
            result = await session.call_tool("solucortex_list_memories", {"limit": 5})
            assert result.isError is False


@pytest.mark.anyio
async def test_request_credentials_reach_the_backend(http_server, fake_backend, monkeypatch):
    monkeypatch.setenv("SOLUCORTEX_API_KEY", "scx_env_should_be_ignored")
    monkeypatch.setenv("SOLUCORTEX_PROJECT_ID", "env-project-should-be-ignored")

    await _call_list_memories(http_server, "scx_tenant_a", "project-a")

    call = fake_backend.captured[-1]
    assert call["headers"]["Authorization"] == "Bearer scx_tenant_a"
    assert call["params"]["project_id"] == "project-a"


@pytest.mark.anyio
async def test_two_tenants_do_not_leak(http_server, fake_backend):
    await _call_list_memories(http_server, "scx_tenant_a", "project-a")
    await _call_list_memories(http_server, "scx_tenant_b", "project-b")

    auths = [c["headers"]["Authorization"] for c in fake_backend.captured]
    projects = [c["params"]["project_id"] for c in fake_backend.captured]
    assert auths == ["Bearer scx_tenant_a", "Bearer scx_tenant_b"]
    assert projects == ["project-a", "project-b"]


@pytest.mark.anyio
async def test_unauthenticated_request_is_401(http_server):
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{http_server}/mcp",
            json={},
            headers={"Accept": "application/json, text/event-stream"},
        )
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_healthz_open(http_server):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{http_server}/healthz")
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_without_project_id_the_backend_infers_it(http_server, fake_backend):
    # SCX-MCP-14: sin X-Solucortex-Project ni argumento, la tool NO envia project_id
    # y el backend lo infiere desde la API key.
    async with streamablehttp_client(
        f"{http_server}/mcp", headers={"Authorization": "Bearer scx_tenant_c"}
    ) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("solucortex_list_memories", {"limit": 2})
            assert result.isError is False
            result2 = await session.call_tool(
                "solucortex_search", {"query": "auth", "limit": 3}
            )
            assert result2.isError is False

    list_call = fake_backend.captured[-2]
    assert "project_id" not in (list_call["params"] or {})
    search_call = fake_backend.captured[-1]
    assert "project_id" not in (search_call["json"] or {})
    assert search_call["headers"]["Authorization"] == "Bearer scx_tenant_c"
