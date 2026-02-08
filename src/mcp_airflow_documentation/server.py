"""FastMCP server for Apache Airflow documentation search."""

from pathlib import Path

from fastmcp import FastMCP

from mcp_airflow_documentation.database import DocumentDatabase

# Initialise MCP server
mcp = FastMCP("Airflow Documentation")


def get_db_path() -> Path:
    """Get the database path.

    Returns:
        Path to the database file.
    """
    # Use data directory relative to package
    package_dir = Path(__file__).parent.parent.parent
    data_dir = package_dir / "data"
    return data_dir / "airflow-docs.db"


def get_db() -> DocumentDatabase:
    """Get database instance.

    Returns:
        DocumentDatabase instance.
    """
    db_path = get_db_path()
    if not db_path.exists():
        raise FileNotFoundError(
            f"Database not found at {db_path}. "
            "Please run 'airflow-docs-index index' to create the database."
        )
    return DocumentDatabase(db_path)


@mcp.tool()
def search_documentation(
    query: str,
    source: str | None = None,
    section: str | None = None,
    limit: int = 10,
) -> str:
    """Search Apache Airflow documentation.

    Search across both Airflow core documentation and Python client documentation
    using full-text search with ranking.

    Args:
        query: Search query string
        source: Optional source filter ('airflow-core' or 'airflow-python-client')
        section: Optional section filter (e.g., 'Core Concepts', 'Operators')
        limit: Maximum number of results (default: 10, max: 50)

    Returns:
        Formatted search results with titles, URLs, and snippets
    """
    if limit > 50:
        limit = 50

    try:
        db = get_db()
        results = db.search(query=query, source=source, section=section, limit=limit)

        if not results:
            return f"No results found for query: {query}"

        # Format results
        output = f"Found {len(results)} results for query: {query}\n\n"

        for i, result in enumerate(results, 1):
            output += f"{i}. {result.format()}\n"

        return output.strip()

    except FileNotFoundError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error searching documentation: {e}"


@mcp.tool()
def read_documentation(source: str, path: str) -> str:
    """Read the full content of a specific documentation page.

    Retrieve the complete text content of a documentation page by its source
    and path. Use this after search_documentation to read the full content.

    Args:
        source: Documentation source ('airflow-core' or 'airflow-python-client')
        path: Relative path to the document (from search results)

    Returns:
        Full document content with metadata
    """
    try:
        db = get_db()
        doc = db.get_document(source=source, path=path)

        if not doc:
            return f"Document not found: {source}/{path}"

        # Format document
        output = f"# {doc.title}\n\n"
        output += f"**Source:** {source}\n"
        output += f"**Section:** {doc.section}\n"
        output += f"**URL:** {doc.url}\n\n"

        if doc.description:
            output += f"**Description:** {doc.description}\n\n"

        output += "---\n\n"
        output += doc.content

        return output

    except FileNotFoundError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error reading documentation: {e}"


@mcp.tool()
def get_sections(source: str | None = None) -> str:
    """Get list of available documentation sections.

    Retrieve all unique sections to help narrow down searches.

    Args:
        source: Optional source filter ('airflow-core' or 'airflow-python-client')

    Returns:
        List of available sections
    """
    try:
        db = get_db()
        sections = db.get_sections(source=source)

        if not sections:
            return "No sections found"

        source_display = f" ({source})" if source else ""
        output = f"Available sections{source_display}:\n\n"

        for section in sections:
            output += f"- {section}\n"

        return output.strip()

    except FileNotFoundError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error getting sections: {e}"


@mcp.tool()
def get_statistics() -> str:
    """Get documentation database statistics.

    Returns counts of indexed documents by source and total counts.

    Returns:
        Database statistics
    """
    try:
        db = get_db()
        stats = db.get_stats()

        output = "Airflow Documentation Statistics\n\n"
        output += f"Airflow Core Documentation: {stats['airflow-core']} documents\n"
        output += f"Python Client Documentation: {stats['airflow-python-client']} documents\n"
        output += f"Total Documents: {stats['total']}\n"

        return output

    except FileNotFoundError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error getting statistics: {e}"


def main() -> None:
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
