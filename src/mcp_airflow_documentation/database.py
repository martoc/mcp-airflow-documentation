"""SQLite FTS5 database operations for Airflow documentation."""

import re
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from mcp_airflow_documentation.models import Document, SearchResult


class DocumentDatabase:
    """Manages the SQLite FTS5 database for documentation search."""

    def __init__(self, db_path: Path) -> None:
        """Initialise database with the given path.

        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = db_path
        self._initialise_schema()

    @staticmethod
    def _sanitise_query(query: str) -> str:
        """Sanitise user query for FTS5 MATCH clause.

        FTS5 uses special characters for query operators. This method
        escapes problematic characters to prevent syntax errors.

        Args:
            query: Raw user query string.

        Returns:
            Sanitised query string safe for FTS5 MATCH.
        """
        # FTS5 special characters that have query syntax meaning
        # Including hyphen to prevent "no such column" errors with hyphenated terms
        fts5_special_chars = r'[.():*"\-]'

        # FTS5 boolean operators (case insensitive)
        fts5_operators = re.compile(r"\b(AND|OR|NOT)\b", re.IGNORECASE)

        # Check if query contains special characters or operators
        if re.search(fts5_special_chars, query) or fts5_operators.search(query):
            # Escape double quotes by doubling them
            query = query.replace('"', '""')
            # Wrap in quotes to treat as literal phrase
            return f'"{query}"'

        return query

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager for database connections.

        Yields:
            SQLite connection with Row factory enabled.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _initialise_schema(self) -> None:
        """Create database schema if it doesn't exist."""
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    path TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    section TEXT,
                    url TEXT,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(source, path)
                );

                CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
                    title,
                    description,
                    content,
                    content='documents',
                    content_rowid='id',
                    tokenize='porter unicode61'
                );

                CREATE TRIGGER IF NOT EXISTS documents_ai AFTER INSERT ON documents BEGIN
                    INSERT INTO documents_fts(rowid, title, description, content)
                    VALUES (new.id, new.title, new.description, new.content);
                END;

                CREATE TRIGGER IF NOT EXISTS documents_ad AFTER DELETE ON documents BEGIN
                    INSERT INTO documents_fts(documents_fts, rowid, title, description, content)
                    VALUES ('delete', old.id, old.title, old.description, old.content);
                END;

                CREATE TRIGGER IF NOT EXISTS documents_au AFTER UPDATE ON documents BEGIN
                    INSERT INTO documents_fts(documents_fts, rowid, title, description, content)
                    VALUES ('delete', old.id, old.title, old.description, old.content);
                    INSERT INTO documents_fts(rowid, title, description, content)
                    VALUES (new.id, new.title, new.description, new.content);
                END;

                CREATE INDEX IF NOT EXISTS idx_documents_section ON documents(section);
                CREATE INDEX IF NOT EXISTS idx_documents_source ON documents(source);
                CREATE INDEX IF NOT EXISTS idx_documents_source_section
                    ON documents(source, section);
            """)
            conn.commit()

    def upsert_document(self, doc: Document) -> None:
        """Insert or update a document.

        Args:
            doc: Document to insert or update.
        """
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO documents (source, path, title, description, section, url, content)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source, path) DO UPDATE SET
                    title = excluded.title,
                    description = excluded.description,
                    section = excluded.section,
                    url = excluded.url,
                    content = excluded.content,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    doc.source,
                    doc.path,
                    doc.title,
                    doc.description,
                    doc.section,
                    doc.url,
                    doc.content,
                ),
            )
            conn.commit()

    def search(
        self,
        query: str,
        source: str | None = None,
        section: str | None = None,
        limit: int = 10,
    ) -> list[SearchResult]:
        """Search documents using FTS5.

        Args:
            query: Search query string.
            source: Optional source filter ('airflow-core' or 'airflow-python-client').
            section: Optional section filter.
            limit: Maximum number of results.

        Returns:
            List of SearchResult instances ordered by relevance.
        """
        # Sanitise query to prevent FTS5 syntax errors
        sanitised_query = self._sanitise_query(query)

        with self._get_connection() as conn:
            # Build query with optional filters
            sql = """
                SELECT
                    d.source,
                    d.path,
                    d.title,
                    d.url,
                    d.section,
                    snippet(documents_fts, 2, '<mark>', '</mark>', '...', 64) as snippet,
                    bm25(documents_fts, 5.0, 2.0, 1.0) as score
                FROM documents_fts
                JOIN documents d ON documents_fts.rowid = d.id
                WHERE documents_fts MATCH ?
            """
            params: list[str | int] = [sanitised_query]

            if source:
                sql += " AND d.source = ?"
                params.append(source)

            if section:
                sql += " AND d.section = ?"
                params.append(section)

            sql += " ORDER BY score LIMIT ?"
            params.append(limit)

            cursor = conn.execute(sql, params)
            results = []
            for row in cursor.fetchall():
                results.append(
                    SearchResult(
                        source=row["source"],
                        path=row["path"],
                        title=row["title"],
                        url=row["url"],
                        section=row["section"],
                        snippet=row["snippet"],
                        score=abs(row["score"]),  # BM25 returns negative scores
                    )
                )
            return results

    def get_document(self, source: str, path: str) -> Document | None:
        """Retrieve a document by source and path.

        Args:
            source: Documentation source ('airflow-core' or 'airflow-python-client').
            path: Relative path to the document.

        Returns:
            Document instance or None if not found.
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM documents WHERE source = ? AND path = ?",
                (source, path),
            )
            row = cursor.fetchone()
            if row:
                return Document(
                    source=row["source"],
                    path=row["path"],
                    title=row["title"],
                    description=row["description"],
                    section=row["section"],
                    content=row["content"],
                    url=row["url"],
                )
            return None

    def clear(self, source: str | None = None) -> None:
        """Clear documents from the database.

        Args:
            source: Optional source filter. If None, clears all documents.
        """
        with self._get_connection() as conn:
            if source:
                conn.execute("DELETE FROM documents WHERE source = ?", (source,))
            else:
                conn.execute("DELETE FROM documents")
            conn.commit()

    def get_document_count(self, source: str | None = None) -> int:
        """Return the number of indexed documents.

        Args:
            source: Optional source filter. If None, returns total count.

        Returns:
            Count of documents in the database.
        """
        with self._get_connection() as conn:
            if source:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM documents WHERE source = ?", (source,)
                )
            else:
                cursor = conn.execute("SELECT COUNT(*) FROM documents")
            result = cursor.fetchone()
            return int(result[0]) if result else 0

    def get_stats(self) -> dict[str, int]:
        """Get document counts by source.

        Returns:
            Dictionary mapping source names to document counts.
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT source, COUNT(*) as count
                FROM documents
                GROUP BY source
                """
            )
            stats = {row["source"]: row["count"] for row in cursor.fetchall()}

            # Ensure both sources are present in the output
            return {
                "airflow-core": stats.get("airflow-core", 0),
                "airflow-python-client": stats.get("airflow-python-client", 0),
                "total": sum(stats.values()),
            }

    def get_sections(self, source: str | None = None) -> list[str]:
        """Get list of unique sections.

        Args:
            source: Optional source filter. If None, returns sections from all sources.

        Returns:
            Sorted list of unique section names.
        """
        with self._get_connection() as conn:
            if source:
                cursor = conn.execute(
                    "SELECT DISTINCT section FROM documents WHERE source = ? ORDER BY section",
                    (source,),
                )
            else:
                cursor = conn.execute(
                    "SELECT DISTINCT section FROM documents ORDER BY section"
                )
            return [row["section"] for row in cursor.fetchall()]
