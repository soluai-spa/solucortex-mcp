"""SCX-MCP-13: the server ships usage methodology as MCP `instructions` on initialize."""

import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from solucortex_mcp.server import INSTRUCTIONS, mcp


def test_instructions_cover_the_workflow_and_rules():
    assert mcp.instructions == INSTRUCTIONS
    for required in (
        "solucortex_recall",
        "solucortex_search",
        "solucortex_remember",
        "architecture",
        "external_integration",
        "never store secrets",
        "pending",
    ):
        assert required in INSTRUCTIONS, f"missing: {required}"


@pytest.mark.anyio
async def test_initialize_exposes_instructions_to_clients(http_server):
    async with streamablehttp_client(
        f"{http_server}/mcp", headers={"Authorization": "Bearer scx_test"}
    ) as (read, write, _):
        async with ClientSession(read, write) as session:
            result = await session.initialize()
    assert result.instructions is not None
    assert "solucortex_recall" in result.instructions
