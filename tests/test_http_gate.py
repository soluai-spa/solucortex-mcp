"""HTTP surface of the remote mode: /healthz open, MCP endpoint gated by Bearer key."""

import httpx


def test_health_needs_no_auth(http_server):
    # /health is the public path (Cloud Run's frontend intercepts /healthz); both work.
    for path in ("/health", "/healthz"):
        resp = httpx.get(f"{http_server}{path}")
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


def test_public_host_header_is_accepted(http_server):
    # Regression (Cloud Run): newer SDKs enable DNS-rebinding protection with a localhost
    # allowlist and 421-reject public Hosts. We disable it — this must never return 421.
    resp = httpx.post(
        f"{http_server}/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "t", "version": "0"},
            },
        },
        headers={
            "Authorization": "Bearer scx_test",
            "Accept": "application/json, text/event-stream",
            "Host": "mcp.solucortex.ai",
        },
    )
    assert resp.status_code == 200


def test_mcp_endpoint_with_key_passes_the_gate(http_server):
    # Invalid MCP payload on purpose: anything but 401 proves the auth gate let it through.
    resp = httpx.post(
        f"{http_server}/mcp",
        json={},
        headers={"Authorization": "Bearer scx_test", "Accept": "application/json, text/event-stream"},
    )
    assert resp.status_code != 401


def test_anonymous_initialize_is_allowed(http_server):
    # Directory probers (e.g. Glama health checks) do an unauthenticated handshake.
    resp = httpx.post(
        f"{http_server}/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "initialize",
              "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                         "clientInfo": {"name": "probe", "version": "0"}}},
        headers={"Accept": "application/json, text/event-stream"},
    )
    assert resp.status_code == 200


def test_anonymous_tool_call_is_still_401(http_server):
    resp = httpx.post(
        f"{http_server}/mcp",
        json={"jsonrpc": "2.0", "id": 2, "method": "tools/call",
              "params": {"name": "solucortex_list_memories", "arguments": {}}},
        headers={"Accept": "application/json, text/event-stream"},
    )
    assert resp.status_code == 401


def test_anonymous_introspection_methods_are_allowed(http_server):
    for method in ("resources/list", "prompts/list"):
        resp = httpx.post(
            f"{http_server}/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": method, "params": {}},
            headers={"Accept": "application/json, text/event-stream"},
        )
        assert resp.status_code != 401, method


def test_anonymous_get_passes_through_to_transport(http_server):
    # SSE listen stream / probes: never a 401. The transport may hold the stream open,
    # so read only the status line without consuming the body.
    with httpx.stream(
        "GET", f"{http_server}/mcp", headers={"Accept": "text/event-stream"}, timeout=5
    ) as resp:
        assert resp.status_code != 401
