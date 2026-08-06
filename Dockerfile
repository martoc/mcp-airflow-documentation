FROM python:3.12-slim

# Disable FastMCP's startup update check; the container has no need to
# reach PyPI at runtime
ENV FASTMCP_CHECK_FOR_UPDATES=off

# Install git for cloning documentation repositories
RUN apt-get update && \
    apt-get install -y git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files
COPY pyproject.toml uv.lock README.md ./
COPY src/ src/
COPY data/ data/

# Install dependencies from the committed lockfile, baking them into the
# image at build time
RUN uv sync --locked --no-dev

# Pre-index both documentation sources at build time
RUN uv run --no-sync airflow-docs-index index

EXPOSE 8000

# Run the MCP server directly from the baked venv so no dependency
# resolution happens on container start
CMD ["/app/.venv/bin/mcp-airflow-documentation"]
