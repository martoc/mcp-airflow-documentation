"""Tests for indexer."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from mcp_airflow_documentation.database import DocumentDatabase
from mcp_airflow_documentation.indexer import AirflowDocsIndexer


def test_index_directory_with_rst_files() -> None:
    """Test indexing directory with RST files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = DocumentDatabase(db_path)
        indexer = AirflowDocsIndexer(db)

        # Create test RST files
        docs_path = Path(tmpdir) / "docs"
        docs_path.mkdir()

        (docs_path / "concepts").mkdir()
        (docs_path / "concepts" / "dags.rst").write_text(
            """
DAGs
====

A DAG is a Directed Acyclic Graph.
            """.strip()
        )

        (docs_path / "operators").mkdir()
        (docs_path / "operators" / "bash.rst").write_text(
            """
Bash Operator
=============

Run bash commands.
            """.strip()
        )

        # Index the directory
        from mcp_airflow_documentation.parsers import RstDocumentParser

        parser = RstDocumentParser(
            source="airflow-core",
            base_url="https://airflow.apache.org/docs/apache-airflow/stable",
        )
        count = indexer._index_directory(docs_path, docs_path, parser)

        assert count == 2
        assert db.get_document_count() == 2

        # Verify documents
        doc1 = db.get_document("airflow-core", "concepts/dags.rst")
        assert doc1 is not None
        assert doc1.title == "DAGs"

        doc2 = db.get_document("airflow-core", "operators/bash.rst")
        assert doc2 is not None
        assert doc2.title == "Bash Operator"


def test_index_directory_with_markdown_files() -> None:
    """Test indexing directory with Markdown files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = DocumentDatabase(db_path)
        indexer = AirflowDocsIndexer(db)

        # Create test Markdown files
        docs_path = Path(tmpdir) / "docs"
        docs_path.mkdir()

        (docs_path / "api").mkdir()
        (docs_path / "api" / "client.md").write_text(
            """---
title: Client API
---

# Client API

Python client for Airflow.
            """.strip()
        )

        (docs_path / "api" / "dags.md").write_text(
            """---
title: DAGs API
---

# DAGs API

Manage DAGs via API.
            """.strip()
        )

        # Index the directory
        from mcp_airflow_documentation.parsers import MarkdownDocumentParser

        parser = MarkdownDocumentParser(
            source="airflow-python-client",
            base_url="https://airflow.apache.org/docs/apache-airflow-client",
        )
        count = indexer._index_directory(docs_path, docs_path, parser)

        assert count == 2
        assert db.get_document_count() == 2

        # Verify documents
        doc1 = db.get_document("airflow-python-client", "api/client.md")
        assert doc1 is not None
        assert doc1.title == "Client API"

        doc2 = db.get_document("airflow-python-client", "api/dags.md")
        assert doc2 is not None
        assert doc2.title == "DAGs API"


def test_index_directory_skips_hidden_files() -> None:
    """Test that hidden files are skipped during indexing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = DocumentDatabase(db_path)
        indexer = AirflowDocsIndexer(db)

        # Create test files including hidden directory
        docs_path = Path(tmpdir) / "docs"
        docs_path.mkdir()

        (docs_path / "visible.rst").write_text(
            """
Visible
=======

Visible content.
            """.strip()
        )

        hidden_dir = docs_path / ".hidden"
        hidden_dir.mkdir()
        (hidden_dir / "hidden.rst").write_text(
            """
Hidden
======

Hidden content.
            """.strip()
        )

        # Index the directory
        from mcp_airflow_documentation.parsers import RstDocumentParser

        parser = RstDocumentParser(
            source="airflow-core",
            base_url="https://airflow.apache.org/docs/apache-airflow/stable",
        )
        count = indexer._index_directory(docs_path, docs_path, parser)

        # Only visible file should be indexed
        assert count == 1
        assert db.get_document_count() == 1


def test_index_source_airflow_core() -> None:
    """Test indexing airflow-core source with mocked git operations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = DocumentDatabase(db_path)
        indexer = AirflowDocsIndexer(db)

        # Mock the git clone and file creation
        def mock_clone_and_create_files(*args: object, **kwargs: object) -> None:
            # Get the repo_path from kwargs or args
            repo_path = kwargs.get("repo_path") or (args[1] if len(args) > 1 else None)
            if repo_path:
                docs_path = repo_path / indexer.AIRFLOW_CORE_DOCS_PATH
                docs_path.mkdir(parents=True, exist_ok=True)
                (docs_path / "test.rst").write_text(
                    """
Test
====

Test content.
                    """.strip()
                )

        with patch.object(indexer, "_clone_repo", side_effect=mock_clone_and_create_files):
            count = indexer.index_source("airflow-core")

        assert count == 1
        assert db.get_document_count(source="airflow-core") == 1


def test_index_source_python_client() -> None:
    """Test indexing python-client source with mocked git operations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = DocumentDatabase(db_path)
        indexer = AirflowDocsIndexer(db)

        # Mock the git clone and file creation
        def mock_clone_and_create_files(*args: object, **kwargs: object) -> None:
            repo_path = kwargs.get("repo_path") or (args[1] if len(args) > 1 else None)
            if repo_path:
                docs_path = repo_path / indexer.PYTHON_CLIENT_DOCS_PATH
                docs_path.mkdir(parents=True, exist_ok=True)
                (docs_path / "test.md").write_text(
                    """---
title: Test
---

Test content.
                    """.strip()
                )

        with patch.object(indexer, "_clone_repo", side_effect=mock_clone_and_create_files):
            count = indexer.index_source("airflow-python-client")

        assert count == 1
        assert db.get_document_count(source="airflow-python-client") == 1


def test_index_source_invalid_source() -> None:
    """Test that invalid source raises ValueError."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = DocumentDatabase(db_path)
        indexer = AirflowDocsIndexer(db)

        try:
            indexer.index_source("invalid-source")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Unknown source" in str(e)


def test_index_all_sources() -> None:
    """Test indexing all sources with mocked git operations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = DocumentDatabase(db_path)
        indexer = AirflowDocsIndexer(db)

        # Mock the git clone to create test files
        def mock_clone_and_create_files(*args: object, **kwargs: object) -> None:
            repo_path = kwargs.get("repo_path") or (args[1] if len(args) > 1 else None)
            sparse_path = kwargs.get("sparse_path") or (args[2] if len(args) > 2 else None)

            if repo_path and sparse_path:
                docs_path = repo_path / sparse_path
                docs_path.mkdir(parents=True, exist_ok=True)

                if "airflow-core" in sparse_path:
                    (docs_path / "test.rst").write_text("Test\n====\nContent.")
                else:
                    (docs_path / "test.md").write_text("---\ntitle: Test\n---\nContent.")

        with patch.object(indexer, "_clone_repo", side_effect=mock_clone_and_create_files):
            results = indexer.index_all_sources()

        assert results["airflow-core"] == 1
        assert results["airflow-python-client"] == 1
        assert results["total"] == 2


def test_index_with_rebuild() -> None:
    """Test that rebuild clears existing documents."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = DocumentDatabase(db_path)
        indexer = AirflowDocsIndexer(db)

        # Add some existing documents
        from mcp_airflow_documentation.models import Document

        doc = Document(
            source="airflow-core",
            path="old.rst",
            title="Old",
            description="Old doc",
            section="Test",
            content="Old content",
            url="https://example.com/old.html",
        )
        db.upsert_document(doc)
        assert db.get_document_count() == 1

        # Mock clone to create new files
        def mock_clone_and_create_files(*args: object, **kwargs: object) -> None:
            repo_path = kwargs.get("repo_path") or (args[1] if len(args) > 1 else None)
            sparse_path = kwargs.get("sparse_path") or (args[2] if len(args) > 2 else None)

            if repo_path and sparse_path:
                docs_path = repo_path / sparse_path
                docs_path.mkdir(parents=True, exist_ok=True)
                (docs_path / "new.rst").write_text("New\n===\nNew content.")

        with patch.object(indexer, "_clone_repo", side_effect=mock_clone_and_create_files):
            count = indexer.index_source("airflow-core", rebuild=True)

        # Old document should be gone, only new one should exist
        assert count == 1
        assert db.get_document_count() == 1
        assert db.get_document("airflow-core", "old.rst") is None
        assert db.get_document("airflow-core", "new.rst") is not None
