# SoluCortex MCP server — stdio transport, launched by the MCP client as a subprocess.
FROM python:3.12-slim

# Install uv for fast, reproducible dependency resolution.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src

# Install the package and its dependencies into the system environment.
RUN uv pip install --system --no-cache .

# stdio server: the client keeps stdin open (docker run -i).
ENTRYPOINT ["solucortex-mcp"]
