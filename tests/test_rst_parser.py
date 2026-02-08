"""Tests for RST parser."""

import tempfile
from pathlib import Path

from mcp_airflow_documentation.parsers.rst_parser import RstDocumentParser


def test_parse_basic_rst_file() -> None:
    """Test parsing a basic RST file."""
    parser = RstDocumentParser(
        source="airflow-core",
        base_url="https://airflow.apache.org/docs/apache-airflow/stable",
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        docs_path = Path(tmpdir) / "docs"
        docs_path.mkdir()

        rst_file = docs_path / "concepts" / "dags.rst"
        rst_file.parent.mkdir(parents=True)
        rst_file.write_text(
            """
DAGs
====

A DAG (Directed Acyclic Graph) is the core concept of Airflow.

DAGs are defined using Python code. They represent a collection of tasks
with dependencies between them.
            """.strip()
        )

        doc = parser.parse_file(rst_file, docs_path)

        assert doc is not None
        assert doc.source == "airflow-core"
        assert doc.title == "DAGs"
        assert doc.description is not None
        assert "Directed Acyclic Graph" in doc.description
        assert doc.section == "Concepts"
        assert "DAG" in doc.content
        assert "Python" in doc.content
        assert doc.url == "https://airflow.apache.org/docs/apache-airflow/stable/concepts/dags.html"
        assert doc.path == "concepts/dags.rst"


def test_parse_rst_without_title() -> None:
    """Test parsing RST file without title uses filename."""
    parser = RstDocumentParser(
        source="airflow-core",
        base_url="https://airflow.apache.org/docs/apache-airflow/stable",
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        docs_path = Path(tmpdir) / "docs"
        docs_path.mkdir()

        rst_file = docs_path / "test-file.rst"
        rst_file.write_text("Some content without a proper title.")

        doc = parser.parse_file(rst_file, docs_path)

        assert doc is not None
        assert doc.title == "Test File"  # Derived from filename
        assert doc.section == "Root"


def test_parse_rst_with_code_blocks() -> None:
    """Test that code blocks are excluded from content."""
    parser = RstDocumentParser(
        source="airflow-core",
        base_url="https://airflow.apache.org/docs/apache-airflow/stable",
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        docs_path = Path(tmpdir) / "docs"
        docs_path.mkdir()

        rst_file = docs_path / "example.rst"
        rst_file.write_text(
            """
Example
=======

This is regular text.

.. code-block:: python

   def my_function():
       pass

More regular text.
            """.strip()
        )

        doc = parser.parse_file(rst_file, docs_path)

        assert doc is not None
        assert "regular text" in doc.content.lower()
        # Code blocks should be excluded by TextContentVisitor
        # Note: The visitor skips literal_block nodes


def test_parse_rst_cleans_directives() -> None:
    """Test that RST directives are cleaned from content."""
    parser = RstDocumentParser(
        source="airflow-core",
        base_url="https://airflow.apache.org/docs/apache-airflow/stable",
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        docs_path = Path(tmpdir) / "docs"
        docs_path.mkdir()

        rst_file = docs_path / "directives.rst"
        rst_file.write_text(
            """
Directives
==========

.. note::
   This is a note.

Regular text here.
            """.strip()
        )

        doc = parser.parse_file(rst_file, docs_path)

        assert doc is not None
        # Content cleaning should remove directive syntax
        assert ".." not in doc.content or "note::" not in doc.content


def test_get_supported_extensions() -> None:
    """Test supported file extensions."""
    parser = RstDocumentParser(
        source="airflow-core",
        base_url="https://airflow.apache.org/docs/apache-airflow/stable",
    )

    extensions = parser.get_supported_extensions()
    assert ".rst" in extensions
    assert ".rest" in extensions


def test_parse_invalid_rst() -> None:
    """Test that invalid RST returns None."""
    parser = RstDocumentParser(
        source="airflow-core",
        base_url="https://airflow.apache.org/docs/apache-airflow/stable",
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        docs_path = Path(tmpdir) / "docs"
        docs_path.mkdir()

        # Create a file that doesn't exist
        rst_file = docs_path / "nonexistent.rst"

        doc = parser.parse_file(rst_file, docs_path)
        assert doc is None
