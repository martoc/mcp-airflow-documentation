# Code Style Guide

This document outlines the coding standards and style conventions for the MCP Airflow Documentation project.

## General Principles

- Write clear, maintainable, and well-documented code
- Follow British English in all code, comments, and documentation
- Prefer explicit over implicit
- Use type hints throughout the codebase

## Python Style

### PEP 8 Compliance

Follow [PEP 8](https://pep8.org/) guidelines with these configurations:

- Line length: 100 characters
- Indentation: 4 spaces (no tabs)
- Target version: Python 3.12+

### Type Hints

Use type hints for all function signatures and class attributes:

```python
def search_documentation(
    query: str,
    source: str | None = None,
    limit: int = 10,
) -> list[SearchResult]:
    """Search documentation with type hints."""
    pass
```

Use modern type hint syntax (PEP 604):
- ✅ `str | None` (preferred)
- ❌ `Optional[str]` (avoid)
- ✅ `list[str]` (preferred)
- ❌ `List[str]` (avoid)

### Docstrings

Use Google-style docstrings for all public functions, classes, and methods:

```python
def parse_file(self, file_path: Path, base_path: Path) -> Document | None:
    """Parse a documentation file.

    Args:
        file_path: Absolute path to the file to parse.
        base_path: Base directory path for calculating relative paths.

    Returns:
        Document instance or None if parsing fails.

    Raises:
        ValueError: If file_path is not within base_path.
    """
    pass
```

### Imports

Organise imports in three groups:

1. Standard library imports
2. Third-party imports
3. Local imports

```python
import re
import sqlite3
from pathlib import Path

import docutils.nodes
from fastmcp import FastMCP

from mcp_airflow_documentation.database import DocumentDatabase
from mcp_airflow_documentation.models import Document
```

Sort imports alphabetically within each group. Use absolute imports for local packages.

### Function and Variable Names

- Functions and methods: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private methods: `_leading_underscore`

```python
class DocumentParser:
    DEFAULT_TIMEOUT = 30

    def parse_file(self, file_path: Path) -> Document | None:
        return self._parse_internal(file_path)

    def _parse_internal(self, file_path: Path) -> Document | None:
        pass
```

### Error Handling

Handle exceptions explicitly and provide meaningful error messages:

```python
def get_document(self, source: str, path: str) -> Document | None:
    """Retrieve document by source and path.

    Returns None if not found rather than raising an exception.
    """
    try:
        # Attempt retrieval
        return self._fetch_document(source, path)
    except DatabaseError as e:
        # Log the error and return None for graceful degradation
        logger.error(f"Database error retrieving {source}/{path}: {e}")
        return None
```

### Context Managers

Use context managers for resource management:

```python
@contextmanager
def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
    """Context manager for database connections."""
    conn = sqlite3.connect(self.db_path)
    try:
        yield conn
    finally:
        conn.close()
```

## Project-Specific Conventions

### Source Identifiers

Use these exact strings for source identification:
- `"airflow-core"` for Apache Airflow core documentation
- `"airflow-python-client"` for Python client documentation

### URL Generation

Generate URLs using consistent patterns:

```python
# Airflow core
f"{BASE_URL}/{path.replace('.rst', '.html')}"

# Python client
f"{BASE_URL}/{path.replace('.md', '.html')}"
```

### Database Queries

Use parameterised queries to prevent SQL injection:

```python
# ✅ Good
cursor.execute("SELECT * FROM documents WHERE source = ?", (source,))

# ❌ Bad
cursor.execute(f"SELECT * FROM documents WHERE source = '{source}'")
```

### Parser Interface

All parsers must implement the `DocumentParser` abstract base class:

```python
class MyParser(DocumentParser):
    def parse_file(self, file_path: Path, base_path: Path) -> Document | None:
        """Implementation required."""
        pass

    def get_supported_extensions(self) -> list[str]:
        """Implementation required."""
        pass
```

## Testing

### Test Structure

- One test file per module: `test_<module>.py`
- Use descriptive test names: `test_<functionality>_<scenario>`
- Group related tests in a class when appropriate

```python
def test_search_with_source_filter() -> None:
    """Test search filtering by source."""
    # Arrange
    db = create_test_db()

    # Act
    results = db.search("query", source="airflow-core")

    # Assert
    assert len(results) > 0
    assert all(r.source == "airflow-core" for r in results)
```

### Test Coverage

Maintain minimum 80% test coverage:

```bash
make test  # Runs pytest with coverage report
```

### Fixtures

Use pytest fixtures for common test setup:

```python
@pytest.fixture
def temp_db() -> DocumentDatabase:
    """Create temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db") as f:
        yield DocumentDatabase(Path(f.name))
```

## Tools and Configuration

### Ruff

Use Ruff for linting and formatting:

```bash
make format  # Format code
make lint    # Check for issues
```

Configuration in `pyproject.toml`:
```toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]
```

### MyPy

Use MyPy for static type checking:

```bash
make typecheck
```

Configuration in `pyproject.toml`:
```toml
[tool.mypy]
python_version = "3.12"
strict = true
```

### Pre-commit Workflow

Before committing:

```bash
make build  # Runs lint, typecheck, and test
```

## Documentation

### Code Comments

Use comments sparingly and only when the code isn't self-explanatory:

```python
# ✅ Good comment - explains why
# FTS5 requires special escaping to prevent syntax errors
query = self._sanitise_query(query)

# ❌ Bad comment - states the obvious
# Set the title
title = "Documentation"
```

### README Files

Each module/repository should have:
- `README.md`: Overview and quick start
- `USAGE.md`: Detailed usage instructions
- `CODESTYLE.md`: Style guidelines (this file)
- `CLAUDE.md`: Project context for AI assistants

### API Documentation

Document all public APIs with comprehensive docstrings. Use examples where helpful:

```python
def search(self, query: str, source: str | None = None) -> list[SearchResult]:
    """Search documentation with FTS5.

    Example:
        >>> db = DocumentDatabase(Path("docs.db"))
        >>> results = db.search("DAG scheduling", source="airflow-core")
        >>> print(results[0].title)
        'DAGs'

    Args:
        query: Search query string.
        source: Optional source filter.

    Returns:
        List of SearchResult instances ordered by relevance.
    """
    pass
```

## Git Practices

### Commit Messages

Follow Conventional Commits specification:

```
feat: add support for filtering by section
fix: handle special characters in search queries
docs: update usage guide with examples
test: add tests for markdown parser
refactor: extract URL generation to helper method
```

### Branch Naming

- Features: `feature/xyz`
- Bug fixes: `bugfix/xyz`
- Hotfixes: `hotfix/xyz`

### Pull Requests

- Create PRs for all changes (never push directly to main)
- Include tests for new functionality
- Update documentation as needed
- Ensure `make build` passes

## Performance Guidelines

### Database Operations

- Use FTS5 for full-text search (not LIKE queries)
- Create indexes for frequently queried columns
- Use connection pooling for concurrent access

### File Operations

- Use `pathlib.Path` instead of string manipulation
- Close file handles properly (use context managers)
- Use streaming for large files

### Memory Management

- Use generators for large result sets
- Clean up temporary files and directories
- Avoid loading entire files into memory when possible

## Security

### Input Validation

Always validate and sanitise user input:

```python
def _sanitise_query(self, query: str) -> str:
    """Sanitise FTS5 query to prevent syntax errors."""
    # Escape special characters
    if re.search(r'[.():*"\-]', query):
        query = query.replace('"', '""')
        return f'"{query}"'
    return query
```

### SQL Injection Prevention

Use parameterised queries exclusively:

```python
# ✅ Safe
conn.execute("SELECT * FROM docs WHERE id = ?", (doc_id,))

# ❌ Unsafe
conn.execute(f"SELECT * FROM docs WHERE id = {doc_id}")
```

### Dependency Management

- Pin dependency versions in `pyproject.toml`
- Review dependencies for security vulnerabilities
- Keep dependencies up to date

## Maintenance

### Code Review

All code must be reviewed before merging:
- Check for adherence to style guidelines
- Verify test coverage
- Ensure documentation is updated
- Run `make build` to validate

### Refactoring

When refactoring:
- Maintain backward compatibility when possible
- Update tests to reflect changes
- Document breaking changes in commit messages
- Keep refactoring separate from feature additions

### Deprecation

When deprecating features:
1. Add deprecation warnings
2. Document in CHANGELOG
3. Provide migration path
4. Remove after appropriate grace period
