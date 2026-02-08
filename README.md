# MCP Airflow Documentation

Model Context Protocol (MCP) server for Apache Airflow documentation search.

## Overview

This MCP server provides unified search across Apache Airflow documentation sources:
- **Airflow Core Documentation** (apache/airflow repository) - RST format
- **Python Client Documentation** (apache/airflow-client-python repository) - Markdown format

## Features

- 🔍 **Full-text search** with SQLite FTS5 for fast, ranked results
- 📚 **Multi-source support** - search both Airflow core and Python client docs
- 🎯 **Advanced filtering** - by source (core/client) and section
- 🐳 **Pre-indexed Docker image** - ready to use with no setup
- ⚡ **Fast queries** - typical search latency < 100ms
- 🤖 **Claude Desktop integration** - seamless access through Claude

## Quick Start

### Using Docker (Recommended)

**Option 1: Use pre-built image (fastest)**

```bash
# Pull the pre-built image
docker pull martoc/mcp-airflow-documentation:latest

# Add to Claude Desktop config
{
  "mcpServers": {
    "airflow-docs": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "martoc/mcp-airflow-documentation:latest"]
    }
  }
}
```

**Option 2: Build locally**

```bash
# Build image (includes pre-indexed documentation)
# NOTE: Build takes 2-5 minutes due to documentation indexing
docker build -t mcp-airflow-documentation .

# Add to Claude Desktop config
{
  "mcpServers": {
    "airflow-docs": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "mcp-airflow-documentation"]
    }
  }
}
```

### Local Installation

```bash
# Clone repository
git clone https://github.com/martoc/mcp-airflow-documentation.git
cd mcp-airflow-documentation

# Initialise environment
make init

# Index documentation (takes 2-5 minutes)
make index

# Add to Claude Desktop config
{
  "mcpServers": {
    "airflow-docs": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/mcp-airflow-documentation",
        "run",
        "mcp-airflow-documentation"
      ]
    }
  }
}
```

## Available Tools

### search_documentation
Search across Airflow documentation with optional filtering.

```python
search_documentation(
    query="DAG scheduling",
    source="airflow-core",  # Optional: 'airflow-core' or 'airflow-python-client'
    section="Core Concepts",  # Optional
    limit=10
)
```

### read_documentation
Read the full content of a specific documentation page.

```python
read_documentation(
    source="airflow-core",
    path="concepts/dags.rst"
)
```

### get_sections
List available documentation sections for browsing.

```python
get_sections(source="airflow-core")  # Optional source filter
```

### get_statistics
View database statistics including document counts by source.

```python
get_statistics()
```

## Usage Examples

**Find DAG documentation:**
```
search_documentation(query="DAG scheduling")
→ Returns ranked results from both sources
```

**Search only Python client docs:**
```
search_documentation(query="API authentication", source="airflow-python-client")
→ Returns results only from Python client documentation
```

**Read full document:**
```
read_documentation(source="airflow-core", path="concepts/dags.rst")
→ Returns complete document content with metadata
```

## Development

### Project Structure

```
mcp-airflow-documentation/
├── src/mcp_airflow_documentation/
│   ├── database.py          # SQLite FTS5 with source support
│   ├── models.py            # Document and SearchResult models
│   ├── indexer.py           # Multi-repository orchestration
│   ├── server.py            # FastMCP server with tools
│   ├── cli.py               # CLI for indexing and stats
│   └── parsers/
│       ├── base.py          # Abstract parser interface
│       ├── rst_parser.py    # RST document parser
│       └── markdown_parser.py  # Markdown document parser
├── tests/                   # Comprehensive test suite (97% coverage)
├── data/                    # Database storage
└── docs/                    # Documentation
```

### Commands

```bash
# Run all quality checks
make build              # lint + typecheck + test

# Individual checks
make test              # Run pytest with coverage
make lint              # Run ruff linter
make typecheck         # Run mypy type checker
make format            # Format code with ruff

# Indexing
make index             # Index all documentation
make index-core        # Index only Airflow core
make index-client      # Index only Python client
make stats             # Show database statistics

# Docker
make docker-pull       # Pull pre-built image
make docker-build      # Build Docker image locally
make docker-run        # Run local Docker container
make docker-run-remote # Run pre-built image
```

### Testing

Run the test suite:

```bash
make test
```

Current coverage: **97%** across all modules.

### Architecture

The project combines proven patterns from two reference implementations:

- **RST parsing**: Adapted from [mcp-cloudcustodian-documentation](https://github.com/martoc/mcp-cloudcustodian-documentation)
  - Docutils visitor pattern for metadata/content extraction
  - FTS5 schema and query sanitisation

- **Markdown parsing**: Adapted from [mcp-spark-documentation](https://github.com/martoc/mcp-spark-documentation)
  - Frontmatter handling
  - Jekyll/HTML cleanup

Key design decisions:

1. **Single database with source tracking**: Unified SQLite database with `source` field
2. **Abstract parser interface**: Base class with format-specific implementations
3. **Sparse git checkout**: Clone only docs directories (not entire repos)
4. **BM25 ranking**: Weighted full-text search (5.0, 2.0, 1.0 for title, description, content)

## Database Schema

```sql
CREATE TABLE documents (
    id INTEGER PRIMARY KEY,
    source TEXT NOT NULL,              -- 'airflow-core' or 'airflow-python-client'
    path TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    section TEXT,
    url TEXT,
    content TEXT NOT NULL,
    UNIQUE(source, path)
);

CREATE VIRTUAL TABLE documents_fts USING fts5(
    title, description, content,
    content='documents',
    content_rowid='id',
    tokenize='porter unicode61'
);
```

## Performance

- **Indexing time**: 2-5 minutes (both sources)
- **Search latency**: < 100ms typical
- **Database size**: ~5-10 MB indexed text
- **Memory usage**: ~50-100 MB server runtime
- **Expected documents**: 200-300 core, 50-100 client

## Container Registry

Pre-built Docker images are available:

```bash
docker pull martoc/mcp-airflow-documentation:latest
```

Images are automatically built and published on each release with pre-indexed documentation for immediate use.

## Documentation

- [USAGE.md](USAGE.md) - Detailed usage instructions
- [CODESTYLE.md](CODESTYLE.md) - Coding standards and conventions
- [CLAUDE.md](CLAUDE.md) - Project context for AI assistants

## Requirements

- **For Docker**: Docker or compatible container runtime
- **For local installation**:
  - Python >= 3.12
  - Git (for cloning documentation repositories)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes following [CODESTYLE.md](CODESTYLE.md)
4. Run `make build` to ensure all checks pass
5. Submit a pull request

## License

MIT
