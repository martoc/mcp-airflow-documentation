"""Tests for Markdown parser."""

import tempfile
from pathlib import Path

from mcp_airflow_documentation.parsers.markdown_parser import MarkdownDocumentParser


def test_parse_basic_markdown_file() -> None:
    """Test parsing a basic Markdown file with frontmatter."""
    parser = MarkdownDocumentParser(
        source="airflow-python-client",
        base_url="https://airflow.apache.org/docs/apache-airflow-client",
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        docs_path = Path(tmpdir) / "docs"
        docs_path.mkdir()

        md_file = docs_path / "api" / "client.md"
        md_file.parent.mkdir(parents=True)
        md_file.write_text(
            """---
title: Python Client API
description: API reference for the Airflow Python client
---

# Python Client

The Airflow Python client provides programmatic access to Airflow.

## Installation

Install using pip:

```bash
pip install apache-airflow-client
```

## Usage

Create a client instance and interact with the API.
            """.strip()
        )

        doc = parser.parse_file(md_file, docs_path)

        assert doc is not None
        assert doc.source == "airflow-python-client"
        assert doc.title == "Python Client API"
        assert doc.description == "API reference for the Airflow Python client"
        assert doc.section == "Api"
        assert "Python client" in doc.content
        assert "programmatic access" in doc.content
        # Code blocks should be removed
        assert "pip install" not in doc.content
        assert doc.url == "https://airflow.apache.org/docs/apache-airflow-client/api/client.html"
        assert doc.path == "api/client.md"


def test_parse_markdown_without_frontmatter() -> None:
    """Test parsing Markdown file without frontmatter."""
    parser = MarkdownDocumentParser(
        source="airflow-python-client",
        base_url="https://airflow.apache.org/docs/apache-airflow-client",
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        docs_path = Path(tmpdir) / "docs"
        docs_path.mkdir()

        md_file = docs_path / "test-file.md"
        md_file.write_text(
            """
# Simple Document

This is a simple document without frontmatter.
            """.strip()
        )

        doc = parser.parse_file(md_file, docs_path)

        assert doc is not None
        assert doc.title == "Test File"  # Derived from filename
        assert doc.description is None
        assert doc.section == "Root"


def test_parse_markdown_cleans_html() -> None:
    """Test that HTML is cleaned from content."""
    parser = MarkdownDocumentParser(
        source="airflow-python-client",
        base_url="https://airflow.apache.org/docs/apache-airflow-client",
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        docs_path = Path(tmpdir) / "docs"
        docs_path.mkdir()

        md_file = docs_path / "html.md"
        md_file.write_text(
            """---
title: HTML Test
---

Regular text here.

<div class="note">
HTML content here
</div>

<!-- HTML comment -->

More regular text.
            """.strip()
        )

        doc = parser.parse_file(md_file, docs_path)

        assert doc is not None
        assert "Regular text" in doc.content
        assert "<div" not in doc.content
        assert "<!--" not in doc.content
        assert "HTML comment" not in doc.content


def test_parse_markdown_cleans_links() -> None:
    """Test that Markdown links are cleaned but text is preserved."""
    parser = MarkdownDocumentParser(
        source="airflow-python-client",
        base_url="https://airflow.apache.org/docs/apache-airflow-client",
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        docs_path = Path(tmpdir) / "docs"
        docs_path.mkdir()

        md_file = docs_path / "links.md"
        md_file.write_text(
            """---
title: Links Test
---

Check out the [Airflow documentation](https://airflow.apache.org) for more info.

![Airflow Logo](logo.png)
            """.strip()
        )

        doc = parser.parse_file(md_file, docs_path)

        assert doc is not None
        assert "Airflow documentation" in doc.content
        assert "https://airflow.apache.org" not in doc.content
        assert "![" not in doc.content
        assert "logo.png" not in doc.content


def test_parse_markdown_removes_headers() -> None:
    """Test that Markdown header symbols are removed."""
    parser = MarkdownDocumentParser(
        source="airflow-python-client",
        base_url="https://airflow.apache.org/docs/apache-airflow-client",
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        docs_path = Path(tmpdir) / "docs"
        docs_path.mkdir()

        md_file = docs_path / "headers.md"
        md_file.write_text(
            """---
title: Headers Test
---

# Main Header

## Subheader

### Third Level

Regular text.
            """.strip()
        )

        doc = parser.parse_file(md_file, docs_path)

        assert doc is not None
        assert "Main Header" in doc.content
        assert "Subheader" in doc.content
        assert "##" not in doc.content
        assert "###" not in doc.content


def test_get_supported_extensions() -> None:
    """Test supported file extensions."""
    parser = MarkdownDocumentParser(
        source="airflow-python-client",
        base_url="https://airflow.apache.org/docs/apache-airflow-client",
    )

    extensions = parser.get_supported_extensions()
    assert ".md" in extensions
    assert ".markdown" in extensions


def test_parse_nonexistent_file() -> None:
    """Test that nonexistent file returns None."""
    parser = MarkdownDocumentParser(
        source="airflow-python-client",
        base_url="https://airflow.apache.org/docs/apache-airflow-client",
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        docs_path = Path(tmpdir) / "docs"
        docs_path.mkdir()

        md_file = docs_path / "nonexistent.md"

        doc = parser.parse_file(md_file, docs_path)
        assert doc is None
