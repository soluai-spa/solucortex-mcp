"""HTTP surface of the remote mode: /healthz open, MCP endpoint gated by Bearer key."""

import httpx


def test_healthz_needs_no_auth(http_server):
    resp = httpx.get(f"{http_server}/healthz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_mcp_endpoint_without_key_is_401(http_server):
    resp = httpx.post(f"{http_server}/mcp", json={})
    assert resp.status_code == 401
    assert resp.headers["www-authenticate"] == "Bearer"
    assert "Authorization: Bearer" in resp.json()["error"]


def test_mcp_endpoint_with_malformed_auth_is_401(http_server):
    resp = httpx.post(f"{http_server}/mcp", json={}, headers={"Authorization": "Token abc"})
    assert resp.status_code == 401


def test_mcp_endpoint_with_key_passes_the_gate(http_server):
    # Invalid MCP payload on purpose: anything but 401 proves the auth gate let it through.
    resp = httpx.post(
        f"{http_server}/mcp",
        json={},
        headers={"Authorization": "Bearer scx_test", "Accept": "application/json, text/event-stream"},
    )
    assert resp.status_code != 401
