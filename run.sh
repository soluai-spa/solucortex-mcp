#!/usr/bin/env bash
# Launcher for the SoluCortex MCP server.
#
# Per-project credentials: each SoluAI repo has its own SoluCortex API key + project_id in
# its agent env file. This script auto-discovers that file from the directory the MCP client
# launches it in (for Claude Code, the workspace/project root), so the same global MCP
# registration serves every project with the right credentials.
#
# Env file search order (first one that exists AND defines SOLUCORTEX_API_KEY wins):
#   1. $SOLUCORTEX_ENV_FILE     (explicit override)
#   2. $PWD/ai/.env.ai          (SoluAI agent env — common)
#   3. $PWD/ai/.env
#   4. $PWD/.env.ai
#   5. <repo>/.env              (fallback default)
# Credentials never live in the MCP client config; only in these on-disk env files.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

has_key() { [[ -f "$1" ]] && grep -qE '^[[:space:]]*SOLUCORTEX_API_KEY=' "$1"; }

ENV_FILE=""
for candidate in \
  "${SOLUCORTEX_ENV_FILE:-}" \
  "$PWD/ai/.env.ai" \
  "$PWD/ai/.env" \
  "$PWD/.env.ai" \
  "$DIR/.env"; do
  if [[ -n "$candidate" ]] && has_key "$candidate"; then
    ENV_FILE="$candidate"
    break
  fi
done

if [[ -n "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi
# If nothing was found, the server starts anyway and returns an actionable
# "Missing SOLUCORTEX_API_KEY" error on the first tool call.

exec uv run --project "$DIR" solucortex-mcp
