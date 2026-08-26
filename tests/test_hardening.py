"""SCX-MCP-11 hardening: payload limit, key fingerprints, no secrets in logs."""

import logging

import httpx
import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from solucortex_mcp.http_app import MAX_BODY_BYTES
from solucortex_mcp.server import _key_fingerprint


def test_key_fingerprint_is_safe_and_stable():
    fp = _key_fingerprint("scx_super_secret_key")
    assert fp == _key_fingerprint("scx_super_secret_key")
    assert len(fp) == 12
    assert "scx" not in fp and "secret" not in fp
    assert fp != _key_fingerprint("scx_other_key")


def test_oversized_payload_is_413(http_server):
    resp = httpx.post(
        f"{http_server}/mcp",
        content=b"x" * (MAX_BODY_BYTES + 1),
        headers={"Authorization": "Bearer scx_test"},
    )
    assert resp.status_code == 413
    assert "Payload too large" in resp.json()["error"]


class _ListHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.messages: list[str] = []

    def emit(self, record):
        self.messages.append(record.getMessage())


@pytest.mark.anyio
async def test_logs_never_contain_the_api_key(http_server, fake_backend):
    # Our loggers don't propagate (they own a plain-JSON handler), so attach directly.
    capture = _ListHandler()
    loggers = [logging.getLogger(n) for n in ("solucortex_mcp.access", "solucortex_mcp.backend")]
    for lg in loggers:
        lg.addHandler(capture)
    secret = "scx_super_secret_key_do_not_log"
    try:
        async with streamablehttp_client(
            f"{http_server}/mcp",
            headers={"Authorization": f"Bearer {secret}", "X-Solucortex-Project": "p-1"},
        ) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                await session.call_tool("solucortex_list_memories", {"limit": 1})
    finally:
        for lg in loggers:
            lg.removeHandler(capture)

    text = "\n".join(capture.messages)
    assert secret not in text
    assert _key_fingerprint(secret) in text  # traceable without being reversible
    assert '"type": "backend_call"' in text
    assert '"type": "access"' in text
