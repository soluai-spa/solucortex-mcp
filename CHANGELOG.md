# Changelog

## 1.0.0 — 2026-08-26

First public release.

### Highlights
- **Two transports**: local stdio (env-configured) and remote Streamable HTTP — the mode
  behind the hosted server at `https://mcp.solucortex.ai/mcp`.
- **Multi-tenant by design**: in HTTP mode credentials travel with each request
  (`Authorization: Bearer` + optional `X-Solucortex-Project`); the server stores no
  tenant credentials and runs stateless.
- **Key-only configuration**: `project_id` is optional everywhere — the SoluCortex
  backend infers it from the project-bound API key.
- **Embedded methodology**: every client receives the living-memory workflow
  (recall → search → remember, the 9 canonical memory types, secrets rules) as MCP
  `instructions` on initialize.
- **Four tools**: `solucortex_recall`, `solucortex_search`, `solucortex_remember`,
  `solucortex_list_memories`.
- **Hardened public endpoint**: per-IP rate limiting, structured logs with key
  fingerprints (keys are never logged), payload limits.
- 26-test suite (unit, HTTP gate, end-to-end with a real MCP client) gating every
  publish; released to PyPI via Trusted Publishing (OIDC, no stored tokens) and listed
  in the official MCP registry as `io.github.soluai-spa/solucortex-mcp`.
