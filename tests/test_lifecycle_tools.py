"""SCX-MCP-18: lifecycle tools — agents propose, humans govern in the panel."""

import json

import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from solucortex_mcp.server import INSTRUCTIONS

HEADERS = {"Authorization": "Bearer scx_lifecycle_test"}


async def _call(http_server, tool, args):
    async with streamablehttp_client(f"{http_server}/mcp", headers=HEADERS) as (r, w, _):
        async with ClientSession(r, w) as session:
            await session.initialize()
            result = await session.call_tool(tool, args)
            return json.loads(result.content[0].text)


@pytest.mark.anyio
async def test_update_patches_only_given_fields_and_never_status(http_server, fake_backend):
    payload = await _call(http_server, "solucortex_update_memory", {
        "memory_id": "mem-123",
        "content": "Contenido corregido.",
        "importance": 7,
    })

    call = fake_backend.captured[-1]
    assert call["method"] == "PATCH"
    assert call["url"].endswith("/api/v1/memories/mem-123")
    assert call["json"] == {"content": "Contenido corregido.", "importance": 7}
    assert "status" not in call["json"]
    assert payload["ok"] is True
    assert "panel" in payload["action_required"]
    assert "PENDING" in payload["action_required"]


@pytest.mark.anyio
async def test_update_with_nothing_to_change_fails_locally(http_server, fake_backend):
    before = len(fake_backend.captured)
    payload = await _call(http_server, "solucortex_update_memory", {"memory_id": "mem-123"})

    assert payload["ok"] is False
    assert len(fake_backend.captured) == before  # no backend call


@pytest.mark.anyio
async def test_flag_posts_reason_and_requires_human_resolution(http_server, fake_backend):
    payload = await _call(http_server, "solucortex_flag_memory", {
        "memory_id": "mem-456",
        "reason": "Quedó obsoleta tras migrar el índice a HNSW.",
        "suggested_action": "archive",
    })

    call = fake_backend.captured[-1]
    assert call["method"] == "POST"
    assert call["url"].endswith("/api/v1/memories/mem-456/flag")
    assert call["json"]["reason"].startswith("Quedó obsoleta")
    assert call["json"]["suggested_action"] == "archive"
    assert payload["ok"] is True
    assert "panel" in payload["action_required"]


def test_instructions_teach_the_governed_lifecycle():
    for required in (
        "solucortex_update_memory",
        "solucortex_flag_memory",
        "deletion is human-only by design",
        "approve the change in the SoluCortex panel",
    ):
        assert required in INSTRUCTIONS, f"missing: {required}"
