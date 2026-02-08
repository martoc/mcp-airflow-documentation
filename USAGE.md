# Usage Guide

This guide covers how to use the MCP Airflow Documentation server.

## Installation

### Local Installation

```bash
# Clone the repository
git clone https://github.com/martoc/mcp-airflow-documentation.git
cd mcp-airflow-documentation

# Initialise development environment
make init

# Index documentation
make index
```

### Docker Installation

**Option 1: Use pre-built image (fastest)**

```bash
# Pull the pre-built image
docker pull martoc/mcp-airflow-documentation:latest

# Run the server
docker run -i --rm martoc/mcp-airflow-documentation:latest
```

**Option 2: Build locally**

```bash
# Build Docker image (includes pre-indexed documentation)
make docker-build

# Run the server
make docker-run
```

## Indexing Documentation

### Index All Sources

Index both Airflow core and Python client documentation:

```bash
airflow-docs-index index
```

### Index Specific Source

Index only Airflow core documentation:

```bash
airflow-docs-index index --source airflow-core
```

Index only Python client documentation:

```bash
airflow-docs-index index --source airflow-python-client
```

### Rebuild Index

Clear existing documents and rebuild:

```bash
airflow-docs-index index --rebuild
```

### Custom Branch

Index from a specific git branch:

```bash
airflow-docs-index index --branch v2-9-stable
```

### Custom Database Path

Use a custom database location:

```bash
airflow-docs-index index --db-path /path/to/custom.db
```

## Database Statistics

View indexed document counts:

```bash
airflow-docs-index stats
```

Output:
```
Database: /path/to/airflow-docs.db

Document counts:
  Airflow Core: 245
  Python Client: 52
  Total: 297

Sections (Airflow Core):
  - Core Concepts
  - Operators
  - Providers
  ... and 12 more

Sections (Python Client):
  - API
  - Root
```

## MCP Server Usage

### Starting the Server

```bash
mcp-airflow-documentation
```

### Claude Desktop Integration

Add to your Claude Desktop configuration (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
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

Or using Docker (pre-built image):

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

Or using Docker (locally built):

```json
{
  "mcpServers": {
    "airflow-docs": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "mcp-airflow-documentation"]
    }
  }
}
```

### Available Tools

#### search_documentation

Search across Airflow documentation with optional filtering.

**Parameters:**
- `query` (string, required): Search query
- `source` (string, optional): Filter by source ('airflow-core' or 'airflow-python-client')
- `section` (string, optional): Filter by section (e.g., 'Core Concepts')
- `limit` (integer, optional): Maximum results (default: 10, max: 50)

**Example queries:**
- `search_documentation(query="DAG scheduling")`
- `search_documentation(query="operators", source="airflow-core")`
- `search_documentation(query="API", source="airflow-python-client", limit=5)`

#### read_documentation

Read the full content of a specific documentation page.

**Parameters:**
- `source` (string, required): Documentation source
- `path` (string, required): Relative path to the document

**Example:**
```
read_documentation(source="airflow-core", path="concepts/dags.rst")
```

#### get_sections

List available documentation sections.

**Parameters:**
- `source` (string, optional): Filter by source

**Examples:**
- `get_sections()` - List all sections
- `get_sections(source="airflow-core")` - List core sections only

#### get_statistics

Get database statistics including document counts by source.

**Example:**
```
get_statistics()
```

## Usage Patterns

### Finding Information

1. **Start with broad search:**
   ```
   search_documentation(query="DAG")
   ```

2. **Narrow by source:**
   ```
   search_documentation(query="DAG", source="airflow-core")
   ```

3. **Filter by section:**
   ```
   search_documentation(query="DAG", source="airflow-core", section="Core Concepts")
   ```

4. **Read full document:**
   ```
   read_documentation(source="airflow-core", path="concepts/dags.rst")
   ```

### Exploring Documentation Structure

1. **Get available sections:**
   ```
   get_sections(source="airflow-core")
   ```

2. **Search within section:**
   ```
   search_documentation(query="operators", section="Operators")
   ```

### API-Specific Queries

1. **Find Python client API docs:**
   ```
   search_documentation(query="client API", source="airflow-python-client")
   ```

2. **Search for specific API methods:**
   ```
   search_documentation(query="create DAG", source="airflow-python-client")
   ```

## Maintenance

### Updating Documentation

To update to the latest documentation:

```bash
airflow-docs-index index --rebuild
```

### Clearing Database

```bash
airflow-docs-index clear
```

### Checking Database Size

```bash
ls -lh data/airflow-docs.db
```

## Troubleshooting

### Database Not Found

If you see "Database not found" error:

```bash
# Index documentation first
airflow-docs-index index
```

### No Results Found

If search returns no results:

1. Check database has documents:
   ```bash
   airflow-docs-index stats
   ```

2. Try broader search terms
3. Remove source/section filters

### Slow Indexing

Indexing can take 2-5 minutes depending on connection speed. The process:

1. Clones repositories with sparse checkout
2. Parses RST and Markdown files
3. Extracts metadata and content
4. Indexes in FTS5 database

### Docker Issues

If Docker image fails to build:

1. Ensure git is available in container
2. Check network connectivity for cloning repositories
3. Verify sufficient disk space

## Performance

- **Search latency**: < 100ms for typical queries
- **Database size**: ~5-10 MB (indexed text)
- **Memory usage**: ~50-100 MB (server runtime)
- **Index time**: 2-5 minutes (both sources)

## Advanced Usage

### Multiple Databases

Use different databases for different purposes:

```bash
# Production database
airflow-docs-index index --db-path /var/lib/airflow-docs/prod.db

# Development database with specific branch
airflow-docs-index index --branch develop --db-path /var/lib/airflow-docs/dev.db
```

### Integration with Scripts

```python
from pathlib import Path
from mcp_airflow_documentation.database import DocumentDatabase

db = DocumentDatabase(Path("data/airflow-docs.db"))
results = db.search("DAG scheduling", limit=5)

for result in results:
    print(f"{result.title}: {result.url}")
```
