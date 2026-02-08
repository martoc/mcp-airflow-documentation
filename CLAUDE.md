# Claude Context: MCP Airflow Documentation

This file provides context for AI assistants (particularly Claude) working on this project.

## Project Overview

**What**: Model Context Protocol (MCP) server that provides unified search across Apache Airflow documentation sources.

**Why**: Developers need quick access to both Airflow core and Python client documentation. This MCP server unifies both sources into a single searchable interface through Claude Desktop.

**How**:
- Clones documentation from GitHub (apache/airflow and apache/airflow-client-python)
- Parses RST files (core docs) and Markdown files (client docs)
- Indexes content in SQLite FTS5 database
- Exposes search tools via FastMCP server

## Architecture

### Multi-Source Strategy

Two documentation sources with different formats:
1. **Airflow Core** (`airflow-core`): RST files from apache/airflow repo
2. **Python Client** (`airflow-python-client`): Markdown files from apache/airflow-client-python repo

Unified in single SQLite database with source tracking field.

### Key Components

```
┌─────────────────────────────────────────────────────────────┐
│                      FastMCP Server                          │
│  (search_documentation, read_documentation, get_sections)    │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              DocumentDatabase (SQLite FTS5)                  │
│  Schema: source, path, title, description, section, content  │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  AirflowDocsIndexer                          │
│  Orchestrates: clone repos → parse files → index database   │
└─────────────┬───────────────────────┬───────────────────────┘
              │                       │
              ▼                       ▼
    ┌─────────────────┐     ┌──────────────────────┐
    │ RstDocumentParser│     │ MarkdownDocumentParser│
    └─────────────────┘     └──────────────────────┘
```

### Parser Architecture

Abstract `DocumentParser` base class with two implementations:

1. **RstDocumentParser**:
   - Uses docutils library
   - Visitor pattern for metadata/content extraction
   - Cleans RST directives and roles
   - URL: `https://airflow.apache.org/docs/apache-airflow/stable/{path}.html`

2. **MarkdownDocumentParser**:
   - Uses python-frontmatter library
   - Extracts YAML frontmatter metadata
   - Cleans Jekyll/HTML markup
   - URL: `https://airflow.apache.org/docs/apache-airflow-client/{path}.html`

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

Key design decisions:
- `source` field enables filtering by documentation source
- FTS5 for fast, ranked full-text search
- BM25 ranking with custom weights (5.0, 2.0, 1.0)
- Query sanitisation to prevent FTS5 syntax errors

## Reference Implementations

This project combines proven patterns from two existing MCP servers:

### Cloud Custodian MCP (RST Parsing)
- Location: `/Users/martoc/Developer/github.com/martoc/mcp-cloudcustodian-documentation`
- Borrowed: RST parser, docutils visitors, FTS5 schema, query sanitisation
- Key file: `src/mcp_cloudcustodian_documentation/parser.py`

### Spark MCP (Markdown Parsing)
- Location: `/Users/martoc/Developer/github.com/martoc/mcp-spark-documentation`
- Borrowed: Markdown parser, frontmatter handling, content cleaning
- Key file: `src/mcp_spark_documentation/parser.py`

## Critical Implementation Details

### Query Sanitisation (IMPORTANT)

FTS5 has special characters that cause syntax errors. Always sanitise queries:

```python
def _sanitise_query(self, query: str) -> str:
    """Prevent FTS5 syntax errors by escaping special chars."""
    fts5_special_chars = r'[.():*"\-]'
    if re.search(fts5_special_chars, query):
        query = query.replace('"', '""')
        return f'"{query}"'  # Wrap in quotes for literal phrase search
    return query
```

Reference: `src/mcp_cloudcustodian_documentation/database.py:25-51`

### Git Sparse Checkout

Clone only documentation directories (not entire repos):

```python
# Configure sparse checkout
subprocess.run(["git", "config", "core.sparseCheckout", "true"], ...)

# Set sparse path
sparse_checkout_file.write_text("docs/apache-airflow")

# Fetch with filter
subprocess.run(["git", "fetch", "--depth", "1", "--filter=blob:none", ...])
```

This reduces clone time from minutes to seconds.

### Source Constants

Always use these exact strings:
- `"airflow-core"` for Apache Airflow core docs
- `"airflow-python-client"` for Python client docs

These are used consistently across database, parsers, indexer, and server.

## File Structure

```
mcp-airflow-documentation/
├── src/mcp_airflow_documentation/
│   ├── database.py          # SQLite FTS5 with source support
│   ├── models.py            # Document and SearchResult dataclasses
│   ├── indexer.py           # Multi-repository orchestration
│   ├── server.py            # FastMCP server with 4 tools
│   ├── cli.py               # CLI for indexing and stats
│   └── parsers/
│       ├── base.py          # Abstract DocumentParser
│       ├── rst_parser.py    # RST implementation
│       └── markdown_parser.py  # Markdown implementation
├── tests/                   # Comprehensive test suite (>80% coverage)
├── data/                    # Database storage (gitignored)
├── Dockerfile               # Pre-indexed Docker image
└── Makefile                 # Build automation
```

## Common Tasks

### Adding a New Parser

1. Subclass `DocumentParser` in `parsers/`
2. Implement `parse_file()` and `get_supported_extensions()`
3. Add tests in `tests/test_<parser>.py`
4. Update `indexer.py` to use new parser

### Modifying Database Schema

1. Update `database.py` schema in `_initialise_schema()`
2. Update `models.py` dataclasses
3. Update all code that creates/reads Documents
4. Require rebuild: users must run `--rebuild`

### Adding MCP Tools

1. Add tool function in `server.py` with `@mcp.tool()` decorator
2. Use type hints (FastMCP generates schema automatically)
3. Add comprehensive docstring (visible to Claude)
4. Handle errors gracefully (return error strings)

## Testing Strategy

### Test Coverage Requirements

Minimum 80% coverage (currently 82%):

```bash
make test  # Runs pytest with coverage report
```

### Test Organisation

- `test_database.py`: Database operations, FTS5 search, source filtering
- `test_rst_parser.py`: RST parsing, metadata extraction, content cleaning
- `test_markdown_parser.py`: Markdown parsing, frontmatter, HTML cleanup
- `test_indexer.py`: Multi-source indexing, git operations (mocked)

### Mocking Strategy

Mock expensive operations (git clones) in tests:

```python
with patch.object(indexer, "_clone_repo", side_effect=mock_clone):
    count = indexer.index_source("airflow-core")
```

## Build and Quality Checks

Run all checks before committing:

```bash
make build  # Runs lint + typecheck + test
```

Individual checks:
- `make format` - Format with Ruff
- `make lint` - Lint with Ruff
- `make typecheck` - Type check with MyPy
- `make test` - Run pytest with coverage

## Docker Strategy

Pre-index documentation at Docker build time:

```dockerfile
# Install dependencies
RUN uv sync --no-dev

# Pre-index at build time (not runtime)
RUN uv run airflow-docs-index index

# Run MCP server
CMD ["uv", "run", "mcp-airflow-documentation"]
```

This creates a ready-to-use image with indexed documentation (~50-100 MB).

## Known Limitations

1. **Docutils Deprecation Warnings**: RST parser uses deprecated OptionParser API. Will need update when docutils 2.0 releases.

2. **No Incremental Updates**: Must rebuild entire index to update. Future enhancement: track git commit hashes and update only changed files.

3. **Section Extraction**: Section names derived from directory structure. May not match actual document organisation.

4. **No Authentication**: Server assumes trusted environment (Claude Desktop). Not suitable for public deployment without auth.

## Performance Characteristics

- **Indexing time**: 2-5 minutes (both sources)
- **Search latency**: < 100ms typical
- **Database size**: ~5-10 MB indexed text
- **Memory usage**: ~50-100 MB server runtime
- **Expected docs**: 200-300 core, 50-100 client

## Troubleshooting

### "Database not found" error
Run `airflow-docs-index index` to create database.

### No search results
1. Check database: `airflow-docs-index stats`
2. Try broader search terms
3. Remove filters (source/section)

### Import errors
Run `uv sync --all-groups` to install dependencies.

## Future Enhancements

Potential improvements (not currently implemented):

1. **Incremental Updates**: Track git commits, update only changed files
2. **Version Support**: Index multiple Airflow versions (2.8, 2.9, etc.)
3. **Code Examples**: Extract and index code snippets separately
4. **Link Following**: Parse cross-references between documents
5. **Search Suggestions**: Provide "did you mean?" for typos
6. **Caching**: Cache frequently accessed documents

## Integration Points

### Claude Desktop

Users can configure in `claude_desktop_config.json` using either the pre-built Docker image or local installation:

**Using pre-built Docker image (recommended):**
```json
{
  "mcpServers": {
    "airflow-docs": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "martoc/mcp-airflow-documentation:latest"]
    }
  }
}
```

**Using local installation:**
```json
{
  "mcpServers": {
    "airflow-docs": {
      "command": "uv",
      "args": ["--directory", "/path/to/project", "run", "mcp-airflow-documentation"]
    }
  }
}
```

### Programmatic Usage

```python
from pathlib import Path
from mcp_airflow_documentation.database import DocumentDatabase

db = DocumentDatabase(Path("data/airflow-docs.db"))
results = db.search("DAG scheduling", source="airflow-core", limit=5)
```

## Contributing Guidelines

When making changes:

1. Follow CODESTYLE.md conventions (British English, type hints, PEP 8)
2. Add tests for new functionality (maintain >80% coverage)
3. Run `make build` before committing
4. Update documentation (README, USAGE, this file)
5. Create PR (never push to main directly)
6. Follow Conventional Commits for commit messages

## Questions to Ask

If working on this project and unsure:

1. **Is this the right source identifier?** Use exact strings: `"airflow-core"` or `"airflow-python-client"`
2. **Should I add a new tool?** Consider if it provides distinct value to Claude users
3. **Is test coverage sufficient?** Run `make test` and check coverage report
4. **Does this break backward compatibility?** Database schema changes require rebuild
5. **Is the error handling graceful?** MCP tools should return error strings, not raise exceptions

## Success Metrics

Project is successful if:
- ✅ Both documentation sources indexed in single database
- ✅ Source-aware search with filtering works correctly
- ✅ URLs generate correctly for both documentation sites
- ✅ Pre-indexed Docker image builds successfully
- ✅ Test coverage >80%
- ✅ `make build` passes all checks
- ✅ MCP server integrates with Claude Desktop
- ✅ All documentation complete and up to date
