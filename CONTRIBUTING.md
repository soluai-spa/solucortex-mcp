# Contributing

Thanks for your interest in improving the SoluCortex MCP server!

## Development setup

```bash
git clone https://github.com/soluai-spa/solucortex-mcp
cd solucortex-mcp
uv sync
```

Run it:

```bash
uv run solucortex-mcp                      # stdio mode
MCP_TRANSPORT=http uv run solucortex-mcp   # HTTP mode on :8080
```

## Tests

The suite must stay green — it gates every PyPI release:

```bash
uv run pytest
```

It covers credential resolution per transport, the HTTP auth gate, hardening
(payload limits, no secrets in logs) and an end-to-end run with a real MCP client.
Add tests for any behavior change.

## Guidelines

- Keep the four tools' contracts stable (`solucortex_recall`, `solucortex_search`,
  `solucortex_remember`, `solucortex_list_memories`).
- Never log or echo API keys — use `_key_fingerprint` for traceability.
- In HTTP mode the environment must stay ignored for credentials (tenant isolation).
- One focused change per PR, with a clear description.

## Releases (maintainers)

Bump `version` in `pyproject.toml` and `server.json`, update `CHANGELOG.md`, then
tag: `git tag vX.Y.Z && git push github vX.Y.Z`. CI publishes to PyPI (trusted
publishing); touching `server.json` on `main` republishes the MCP registry entry.
