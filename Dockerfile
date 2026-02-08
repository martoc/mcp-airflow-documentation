FROM python:3.12-slim

# Install git for cloning documentation repositories
RUN apt-get update && \
    apt-get install -y git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ src/
COPY data/ data/

# Install dependencies
RUN uv sync --no-dev

# Pre-index both documentation sources at build time
RUN uv run airflow-docs-index index

# Run the MCP server
CMD ["uv", "run", "mcp-airflow-documentation"]
