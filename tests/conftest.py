import socket
import threading
import time
import types

import httpx
import pytest
import uvicorn

from solucortex_mcp import server
from solucortex_mcp.http_app import build_http_app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def stdio_mode(monkeypatch):
    monkeypatch.setattr(server, "_http_mode", False)


@pytest.fixture
def http_mode(monkeypatch):
    monkeypatch.setattr(server, "_http_mode", True)


class FakeResponse:
    status_code = 200
    is_success = True

    def json(self):
        return {"data": []}


class FakeAsyncClient:
    """Replaces httpx.AsyncClient in server._request; captures the outgoing call."""

    captured: list[dict] = []

    def __init__(self, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def request(self, method, url, headers=None, json=None, params=None):
        type(self).captured.append(
            {"method": method, "url": url, "headers": headers, "json": json, "params": params}
        )
        return FakeResponse()


@pytest.fixture(scope="session")
def http_server():
    """One live uvicorn server for the whole suite.

    The FastMCP session manager can only start once per process — same as production,
    where build_http_app() runs a single time — so every HTTP test shares this server.
    """
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    config = uvicorn.Config(build_http_app(), host="127.0.0.1", port=port, log_level="warning")
    uv_server = uvicorn.Server(config)
    thread = threading.Thread(target=uv_server.run, daemon=True)
    thread.start()
    deadline = time.time() + 10
    while not uv_server.started:
        if time.time() > deadline:
            raise RuntimeError("uvicorn did not start in 10s")
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    uv_server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture
def fake_backend(monkeypatch):
    # Patch only the server module's httpx reference: the MCP client in the tests
    # must keep using the real httpx.
    FakeAsyncClient.captured = []
    shim = types.SimpleNamespace(
        AsyncClient=FakeAsyncClient,
        TimeoutException=httpx.TimeoutException,
        HTTPError=httpx.HTTPError,
    )
    monkeypatch.setattr(server, "httpx", shim)
    return FakeAsyncClient
