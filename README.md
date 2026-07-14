# SoluCortex MCP

Official [Model Context Protocol](https://modelcontextprotocol.io) server for
**[SoluCortex](https://solucortex.ai)** — living technical memory for AI agents.

Connect any MCP-compatible agent (Claude Code, Claude Desktop, Cursor, Codex, Cline, …) to
your SoluCortex project so it can **recall** the decisions, conventions, risks and architecture
that matter before it works, and **remember** what it learns when it's done.

## Tools

| Tool | What it does | When to use |
|------|--------------|-------------|
| `solucortex_recall` | Builds living context for a task (ranked by semantic similarity + importance) | At the **start** of a task, before touching code |
| `solucortex_search` | Ad-hoc semantic search over the project's memories | Specific questions mid-task |
| `solucortex_remember` | Records a memory (stored `approved` + traced as an authorized agent) | At **close**, or on a relevant technical decision |
| `solucortex_list_memories` | Lists memories without semantic search | Quick inspection / audit |

## Requirements

- A SoluCortex account and a **project API key** (prefix `scx_`) — get it from your
  [SoluCortex dashboard](https://solucortex.ai).
- One of: [`uv`](https://docs.astral.sh/uv/) (recommended), Python ≥ 3.10, or Docker.

## Configuration

The server is configured entirely through environment variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `SOLUCORTEX_API_KEY` | ✅ | Project API key (`scx_…`) |
| `SOLUCORTEX_PROJECT_ID` | recommended | Default project UUID (can be overridden per call) |
| `SOLUCORTEX_URL` | optional | API base URL. Default `https://solucortex.soluai.cl` |

Never commit your API key. Keep it in your MCP client config's `env` block or a local `.env`
(see [`.env.example`](.env.example)).

## Install

### Claude Code

```bash
claude mcp add solucortex \
  -e SOLUCORTEX_API_KEY=scx_xxx \
  -e SOLUCORTEX_PROJECT_ID=your-project-uuid \
  -- uvx --from git+https://github.com/soluai/solucortex-mcp solucortex-mcp
```

(Once published to PyPI: replace the command with `uvx solucortex-mcp`.)

### Claude Desktop / Cursor / Cline (JSON config)

Add to the client's MCP config (`claude_desktop_config.json`, Cursor `mcp.json`, etc.):

```json
{
  "mcpServers": {
    "solucortex": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/soluai/solucortex-mcp", "solucortex-mcp"],
      "env": {
        "SOLUCORTEX_API_KEY": "scx_xxx",
        "SOLUCORTEX_PROJECT_ID": "your-project-uuid"
      }
    }
  }
}
```

### From a local clone

```bash
git clone https://github.com/soluai/solucortex-mcp
cd solucortex-mcp
cp .env.example .env   # fill in your key
./run.sh               # loads .env, then runs via uv
# or, with SOLUCORTEX_* already exported: uv run solucortex-mcp
```

### Docker

```bash
docker build -t solucortex-mcp .
docker run --rm -i \
  -e SOLUCORTEX_API_KEY=scx_xxx \
  -e SOLUCORTEX_PROJECT_ID=your-project-uuid \
  solucortex-mcp
```

The server speaks MCP over **stdio**, so clients launch it as a subprocess (`-i` keeps stdin open).

## Development

```bash
uv sync
uv run solucortex-mcp            # run
python -m py_compile src/solucortex_mcp/server.py   # quick syntax check
npx @modelcontextprotocol/inspector uv run solucortex-mcp   # interactive test
```

## Notes

- Memory `type` vocabulary: the canonical set is `architecture, decision, risk, convention,
  bug_history, tech_debt, sensitive_module, learning, external_integration`. Some backends
  accept an older set (`technical_decision, historical_bug, current_state, task_closure`).
  The server passes `type` through and surfaces `HTTP 422` so you can retry with the other set.
- Never store real secrets in a memory. Record location, type, severity and action taken instead.

## License

MIT — see [LICENSE](LICENSE).
