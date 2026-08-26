# SoluCortex MCP server.
# Default: stdio transport, launched by an MCP client as a subprocess (docker run -i).
# Cloud Run / remote: set MCP_TRANSPORT=http to serve Streamable HTTP on $PORT (default 8080).
FROM python:3.12-slim

# Install uv for fast, reproducible dependency resolution.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src

# Install the package and its dependencies into the system environment.
RUN uv pip install --system --no-cache .

# The server holds no tenant credentials; run as an unprivileged user.
RUN useradd --create-home --uid 1001 mcp
USER mcp

EXPOSE 8080

ENTRYPOINT ["solucortex-mcp"]
