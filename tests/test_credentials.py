"""Credential resolution per transport mode (SCX-MCP-08).

stdio: environment. http: per-request context variables, environment ignored.
"""

from solucortex_mcp import server


class TestStdioMode:
    def test_api_key_from_env(self, stdio_mode, monkeypatch):
        monkeypatch.setenv("SOLUCORTEX_API_KEY", "scx_env_key")
        assert server._api_key() == "scx_env_key"

    def test_project_id_from_env(self, stdio_mode, monkeypatch):
        monkeypatch.setenv("SOLUCORTEX_PROJECT_ID", "env-project")
        assert server._resolve_project_id(None) == "env-project"

    def test_explicit_project_id_wins(self, stdio_mode, monkeypatch):
        monkeypatch.setenv("SOLUCORTEX_PROJECT_ID", "env-project")
        assert server._resolve_project_id("explicit") == "explicit"

    def test_config_error_mentions_env_var(self, stdio_mode, monkeypatch):
        monkeypatch.delenv("SOLUCORTEX_API_KEY", raising=False)
        assert "SOLUCORTEX_API_KEY" in server._config_error()

    def test_missing_project_error_mentions_env_var(self, stdio_mode):
        assert "SOLUCORTEX_PROJECT_ID" in server._missing_project_error()["error"]


class TestHttpMode:
    def test_env_api_key_is_ignored(self, http_mode, monkeypatch):
        monkeypatch.setenv("SOLUCORTEX_API_KEY", "scx_env_key")
        assert server._api_key() is None

    def test_api_key_from_request_context(self, http_mode, monkeypatch):
        monkeypatch.setenv("SOLUCORTEX_API_KEY", "scx_env_key")
        token = server._request_api_key.set("scx_request_key")
        try:
            assert server._api_key() == "scx_request_key"
        finally:
            server._request_api_key.reset(token)

    def test_env_project_id_is_ignored(self, http_mode, monkeypatch):
        monkeypatch.setenv("SOLUCORTEX_PROJECT_ID", "env-project")
        assert server._resolve_project_id(None) is None

    def test_project_id_from_request_context(self, http_mode):
        token = server._request_project_id.set("header-project")
        try:
            assert server._resolve_project_id(None) == "header-project"
        finally:
            server._request_project_id.reset(token)

    def test_explicit_project_id_wins_over_header(self, http_mode):
        token = server._request_project_id.set("header-project")
        try:
            assert server._resolve_project_id("explicit") == "explicit"
        finally:
            server._request_project_id.reset(token)

    def test_config_error_mentions_authorization_header(self, http_mode):
        assert "Authorization: Bearer" in server._config_error()

    def test_missing_project_error_mentions_header(self, http_mode):
        assert "X-Solucortex-Project" in server._missing_project_error()["error"]
