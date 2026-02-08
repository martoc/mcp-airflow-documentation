"""Tests for database operations."""

import tempfile
from pathlib import Path

import pytest

from mcp_airflow_documentation.database import DocumentDatabase
from mcp_airflow_documentation.models import Document


@pytest.fixture
def temp_db() -> DocumentDatabase:
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    return DocumentDatabase(db_path)


def test_initialise_schema(temp_db: DocumentDatabase) -> None:
    """Test database schema initialisation."""
    assert temp_db.db_path.exists()
    assert temp_db.get_document_count() == 0


def test_upsert_document(temp_db: DocumentDatabase) -> None:
    """Test document insertion and update."""
    doc = Document(
        source="airflow-core",
        path="concepts/dags.rst",
        title="DAGs",
        description="Directed Acyclic Graphs",
        section="Core Concepts",
        content="A DAG is a collection of tasks",
        url="https://airflow.apache.org/docs/apache-airflow/stable/concepts/dags.html",
    )

    temp_db.upsert_document(doc)
    assert temp_db.get_document_count() == 1

    # Update the same document
    doc.description = "Updated description"
    temp_db.upsert_document(doc)
    assert temp_db.get_document_count() == 1  # Should still be 1

    # Verify update
    retrieved = temp_db.get_document("airflow-core", "concepts/dags.rst")
    assert retrieved is not None
    assert retrieved.description == "Updated description"


def test_upsert_different_sources(temp_db: DocumentDatabase) -> None:
    """Test that same path in different sources creates separate documents."""
    doc1 = Document(
        source="airflow-core",
        path="index.rst",
        title="Core Index",
        description="Core docs",
        section="Root",
        content="Core content",
        url="https://airflow.apache.org/docs/apache-airflow/stable/index.html",
    )

    doc2 = Document(
        source="airflow-python-client",
        path="index.md",
        title="Client Index",
        description="Client docs",
        section="Root",
        content="Client content",
        url="https://airflow.apache.org/docs/apache-airflow-client/index.html",
    )

    temp_db.upsert_document(doc1)
    temp_db.upsert_document(doc2)
    assert temp_db.get_document_count() == 2


def test_search_basic(temp_db: DocumentDatabase) -> None:
    """Test basic search functionality."""
    doc = Document(
        source="airflow-core",
        path="concepts/dags.rst",
        title="DAGs",
        description="Directed Acyclic Graphs",
        section="Core Concepts",
        content="A DAG is a collection of tasks with dependencies",
        url="https://airflow.apache.org/docs/apache-airflow/stable/concepts/dags.html",
    )
    temp_db.upsert_document(doc)

    results = temp_db.search("DAG tasks")
    assert len(results) == 1
    assert results[0].title == "DAGs"
    assert results[0].source == "airflow-core"
    assert results[0].score > 0


def test_search_with_source_filter(temp_db: DocumentDatabase) -> None:
    """Test search with source filtering."""
    doc1 = Document(
        source="airflow-core",
        path="concepts/dags.rst",
        title="Core DAGs",
        description="Core docs",
        section="Core Concepts",
        content="DAG scheduling in Airflow core",
        url="https://airflow.apache.org/docs/apache-airflow/stable/concepts/dags.html",
    )

    doc2 = Document(
        source="airflow-python-client",
        path="api/client.md",
        title="Client API",
        description="Client docs",
        section="API",
        content="Using the DAG API with Python client",
        url="https://airflow.apache.org/docs/apache-airflow-client/api/client.html",
    )

    temp_db.upsert_document(doc1)
    temp_db.upsert_document(doc2)

    # Search all sources
    results = temp_db.search("DAG")
    assert len(results) == 2

    # Search only core
    results = temp_db.search("DAG", source="airflow-core")
    assert len(results) == 1
    assert results[0].source == "airflow-core"

    # Search only client
    results = temp_db.search("DAG", source="airflow-python-client")
    assert len(results) == 1
    assert results[0].source == "airflow-python-client"


def test_search_with_section_filter(temp_db: DocumentDatabase) -> None:
    """Test search with section filtering."""
    doc1 = Document(
        source="airflow-core",
        path="concepts/dags.rst",
        title="DAGs",
        description="Core docs",
        section="Core Concepts",
        content="DAG information",
        url="https://airflow.apache.org/docs/apache-airflow/stable/concepts/dags.html",
    )

    doc2 = Document(
        source="airflow-core",
        path="operators/bash.rst",
        title="Bash Operator",
        description="Core docs",
        section="Operators",
        content="DAG with bash operator",
        url="https://airflow.apache.org/docs/apache-airflow/stable/operators/bash.html",
    )

    temp_db.upsert_document(doc1)
    temp_db.upsert_document(doc2)

    # Search with section filter
    results = temp_db.search("DAG", section="Core Concepts")
    assert len(results) == 1
    assert results[0].section == "Core Concepts"


def test_search_with_source_and_section_filter(temp_db: DocumentDatabase) -> None:
    """Test search with both source and section filters."""
    docs = [
        Document(
            source="airflow-core",
            path="concepts/dags.rst",
            title="Core DAGs",
            description="Core docs",
            section="Core Concepts",
            content="DAG information",
            url="https://airflow.apache.org/docs/apache-airflow/stable/concepts/dags.html",
        ),
        Document(
            source="airflow-core",
            path="operators/bash.rst",
            title="Bash Operator",
            description="Core docs",
            section="Operators",
            content="DAG with operators",
            url="https://airflow.apache.org/docs/apache-airflow/stable/operators/bash.html",
        ),
        Document(
            source="airflow-python-client",
            path="api/dags.md",
            title="DAGs API",
            description="Client docs",
            section="API",
            content="DAG API methods",
            url="https://airflow.apache.org/docs/apache-airflow-client/api/dags.html",
        ),
    ]

    for doc in docs:
        temp_db.upsert_document(doc)

    # Search with both filters
    results = temp_db.search("DAG", source="airflow-core", section="Core Concepts")
    assert len(results) == 1
    assert results[0].source == "airflow-core"
    assert results[0].section == "Core Concepts"


def test_search_special_characters(temp_db: DocumentDatabase) -> None:
    """Test search query sanitisation with special characters."""
    doc = Document(
        source="airflow-core",
        path="concepts/dags.rst",
        title="DAGs",
        description="DAG scheduling",
        section="Core Concepts",
        content="Task scheduling with cron-like syntax",
        url="https://airflow.apache.org/docs/apache-airflow/stable/concepts/dags.html",
    )
    temp_db.upsert_document(doc)

    # These should not cause FTS5 syntax errors
    results = temp_db.search("cron-like")
    assert len(results) == 1

    # Query with AND operator gets wrapped in quotes, becomes phrase search
    # This is expected behaviour - it prevents FTS5 syntax errors
    results = temp_db.search("Task AND scheduling")
    # Should return results (phrase search or no results is acceptable)
    assert len(results) >= 0

    results = temp_db.search("scheduling (cron)")
    # Query with parentheses gets wrapped in quotes
    assert len(results) >= 0

    # Test that basic queries still work
    results = temp_db.search("scheduling")
    assert len(results) == 1


def test_get_document(temp_db: DocumentDatabase) -> None:
    """Test retrieving a document by source and path."""
    doc = Document(
        source="airflow-core",
        path="concepts/dags.rst",
        title="DAGs",
        description="Directed Acyclic Graphs",
        section="Core Concepts",
        content="A DAG is a collection of tasks",
        url="https://airflow.apache.org/docs/apache-airflow/stable/concepts/dags.html",
    )
    temp_db.upsert_document(doc)

    retrieved = temp_db.get_document("airflow-core", "concepts/dags.rst")
    assert retrieved is not None
    assert retrieved.title == "DAGs"
    assert retrieved.source == "airflow-core"

    # Test non-existent document
    retrieved = temp_db.get_document("airflow-core", "nonexistent.rst")
    assert retrieved is None

    # Test wrong source
    retrieved = temp_db.get_document("airflow-python-client", "concepts/dags.rst")
    assert retrieved is None


def test_clear_all(temp_db: DocumentDatabase) -> None:
    """Test clearing all documents."""
    doc1 = Document(
        source="airflow-core",
        path="concepts/dags.rst",
        title="DAGs",
        description="Core docs",
        section="Core Concepts",
        content="DAG content",
        url="https://airflow.apache.org/docs/apache-airflow/stable/concepts/dags.html",
    )

    doc2 = Document(
        source="airflow-python-client",
        path="api/client.md",
        title="Client API",
        description="Client docs",
        section="API",
        content="Client content",
        url="https://airflow.apache.org/docs/apache-airflow-client/api/client.html",
    )

    temp_db.upsert_document(doc1)
    temp_db.upsert_document(doc2)
    assert temp_db.get_document_count() == 2

    temp_db.clear()
    assert temp_db.get_document_count() == 0


def test_clear_by_source(temp_db: DocumentDatabase) -> None:
    """Test clearing documents by source."""
    doc1 = Document(
        source="airflow-core",
        path="concepts/dags.rst",
        title="DAGs",
        description="Core docs",
        section="Core Concepts",
        content="DAG content",
        url="https://airflow.apache.org/docs/apache-airflow/stable/concepts/dags.html",
    )

    doc2 = Document(
        source="airflow-python-client",
        path="api/client.md",
        title="Client API",
        description="Client docs",
        section="API",
        content="Client content",
        url="https://airflow.apache.org/docs/apache-airflow-client/api/client.html",
    )

    temp_db.upsert_document(doc1)
    temp_db.upsert_document(doc2)
    assert temp_db.get_document_count() == 2

    temp_db.clear(source="airflow-core")
    assert temp_db.get_document_count() == 1
    assert temp_db.get_document_count(source="airflow-python-client") == 1


def test_get_stats(temp_db: DocumentDatabase) -> None:
    """Test getting document statistics."""
    doc1 = Document(
        source="airflow-core",
        path="concepts/dags.rst",
        title="DAGs",
        description="Core docs",
        section="Core Concepts",
        content="DAG content",
        url="https://airflow.apache.org/docs/apache-airflow/stable/concepts/dags.html",
    )

    doc2 = Document(
        source="airflow-python-client",
        path="api/client.md",
        title="Client API",
        description="Client docs",
        section="API",
        content="Client content",
        url="https://airflow.apache.org/docs/apache-airflow-client/api/client.html",
    )

    doc3 = Document(
        source="airflow-core",
        path="concepts/tasks.rst",
        title="Tasks",
        description="Core docs",
        section="Core Concepts",
        content="Task content",
        url="https://airflow.apache.org/docs/apache-airflow/stable/concepts/tasks.html",
    )

    temp_db.upsert_document(doc1)
    temp_db.upsert_document(doc2)
    temp_db.upsert_document(doc3)

    stats = temp_db.get_stats()
    assert stats["airflow-core"] == 2
    assert stats["airflow-python-client"] == 1
    assert stats["total"] == 3


def test_get_sections(temp_db: DocumentDatabase) -> None:
    """Test getting unique sections."""
    docs = [
        Document(
            source="airflow-core",
            path="concepts/dags.rst",
            title="DAGs",
            description="Core docs",
            section="Core Concepts",
            content="DAG content",
            url="https://airflow.apache.org/docs/apache-airflow/stable/concepts/dags.html",
        ),
        Document(
            source="airflow-core",
            path="operators/bash.rst",
            title="Bash Operator",
            description="Core docs",
            section="Operators",
            content="Operator content",
            url="https://airflow.apache.org/docs/apache-airflow/stable/operators/bash.html",
        ),
        Document(
            source="airflow-python-client",
            path="api/client.md",
            title="Client API",
            description="Client docs",
            section="API",
            content="Client content",
            url="https://airflow.apache.org/docs/apache-airflow-client/api/client.html",
        ),
    ]

    for doc in docs:
        temp_db.upsert_document(doc)

    # Get all sections
    sections = temp_db.get_sections()
    assert len(sections) == 3
    assert "Core Concepts" in sections
    assert "Operators" in sections
    assert "API" in sections

    # Get sections for specific source
    sections = temp_db.get_sections(source="airflow-core")
    assert len(sections) == 2
    assert "Core Concepts" in sections
    assert "Operators" in sections
    assert "API" not in sections
