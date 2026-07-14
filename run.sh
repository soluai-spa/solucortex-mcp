#!/usr/bin/env bash
# Local convenience launcher: loads credentials from a .env file (so the API key never
# needs to live in your MCP client config), then runs the server via uv.
#
# Env file search order:
#   1. $SOLUCORTEX_ENV_FILE  (if set)
#   2. <this_dir>/.env       (default)
# Production clients should instead pass SOLUCORTEX_* via their own `env` block (see README).
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SOLUCORTEX_ENV_FILE:-$DIR/.env}"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

exec uv run --project "$DIR" solucortex-mcp
