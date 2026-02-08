"""Indexer for Apache Airflow documentation from multiple repositories."""

import subprocess
import tempfile
from pathlib import Path

from mcp_airflow_documentation.database import DocumentDatabase
from mcp_airflow_documentation.parsers import MarkdownDocumentParser, RstDocumentParser


class AirflowDocsIndexer:
    """Orchestrates indexing of Airflow documentation from multiple sources."""

    # Airflow core repository
    AIRFLOW_CORE_REPO = "https://github.com/apache/airflow.git"
    AIRFLOW_CORE_DOCS_PATH = "docs/apache-airflow"
    AIRFLOW_CORE_SOURCE = "airflow-core"
    AIRFLOW_CORE_BASE_URL = "https://airflow.apache.org/docs/apache-airflow/stable"

    # Python client repository
    PYTHON_CLIENT_REPO = "https://github.com/apache/airflow-client-python.git"
    PYTHON_CLIENT_DOCS_PATH = "docs"
    PYTHON_CLIENT_SOURCE = "airflow-python-client"
    PYTHON_CLIENT_BASE_URL = "https://airflow.apache.org/docs/apache-airflow-client"

    def __init__(self, db: DocumentDatabase) -> None:
        """Initialise indexer with database.

        Args:
            db: DocumentDatabase instance for storing indexed documents.
        """
        self.db = db

    def index_all_sources(
        self, branch: str = "main", rebuild: bool = False
    ) -> dict[str, int]:
        """Index documentation from all sources.

        Args:
            branch: Git branch to checkout.
            rebuild: If True, clear existing documents before indexing.

        Returns:
            Dictionary mapping source names to document counts.
        """
        if rebuild:
            self.db.clear()

        results = {}
        results[self.AIRFLOW_CORE_SOURCE] = self._index_airflow_core(branch)
        results[self.PYTHON_CLIENT_SOURCE] = self._index_python_client(branch)
        results["total"] = sum(results.values())

        return results

    def index_source(self, source: str, branch: str = "main", rebuild: bool = False) -> int:
        """Index documentation from a specific source.

        Args:
            source: Source identifier ('airflow-core' or 'airflow-python-client').
            branch: Git branch to checkout.
            rebuild: If True, clear existing documents for this source before indexing.

        Returns:
            Number of documents indexed.

        Raises:
            ValueError: If source is not recognised.
        """
        if rebuild:
            self.db.clear(source=source)

        if source == self.AIRFLOW_CORE_SOURCE:
            return self._index_airflow_core(branch)
        elif source == self.PYTHON_CLIENT_SOURCE:
            return self._index_python_client(branch)
        else:
            raise ValueError(
                f"Unknown source: {source}. "
                f"Must be '{self.AIRFLOW_CORE_SOURCE}' or '{self.PYTHON_CLIENT_SOURCE}'"
            )

    def _index_airflow_core(self, branch: str) -> int:
        """Index Airflow core documentation.

        Args:
            branch: Git branch to checkout.

        Returns:
            Number of documents indexed.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "airflow"
            docs_path = repo_path / self.AIRFLOW_CORE_DOCS_PATH

            # Clone repository with sparse checkout
            self._clone_repo(
                repo_url=self.AIRFLOW_CORE_REPO,
                repo_path=repo_path,
                sparse_path=self.AIRFLOW_CORE_DOCS_PATH,
                branch=branch,
            )

            # Parse RST files
            parser = RstDocumentParser(
                source=self.AIRFLOW_CORE_SOURCE,
                base_url=self.AIRFLOW_CORE_BASE_URL,
            )

            return self._index_directory(docs_path, docs_path, parser)

    def _index_python_client(self, branch: str) -> int:
        """Index Python client documentation.

        Args:
            branch: Git branch to checkout.

        Returns:
            Number of documents indexed.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "airflow-client-python"
            docs_path = repo_path / self.PYTHON_CLIENT_DOCS_PATH

            # Clone repository with sparse checkout
            self._clone_repo(
                repo_url=self.PYTHON_CLIENT_REPO,
                repo_path=repo_path,
                sparse_path=self.PYTHON_CLIENT_DOCS_PATH,
                branch=branch,
            )

            # Parse Markdown files
            parser = MarkdownDocumentParser(
                source=self.PYTHON_CLIENT_SOURCE,
                base_url=self.PYTHON_CLIENT_BASE_URL,
            )

            return self._index_directory(docs_path, docs_path, parser)

    def _clone_repo(
        self, repo_url: str, repo_path: Path, sparse_path: str, branch: str
    ) -> None:
        """Clone a git repository with sparse checkout.

        Args:
            repo_url: URL of the git repository.
            repo_path: Local path to clone to.
            sparse_path: Path within repository for sparse checkout.
            branch: Git branch to checkout.
        """
        # Create repository directory
        repo_path.mkdir(parents=True, exist_ok=True)

        # Initialise git repository
        subprocess.run(
            ["git", "init"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Configure sparse checkout
        subprocess.run(
            ["git", "config", "core.sparseCheckout", "true"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Set sparse checkout path
        sparse_checkout_file = repo_path / ".git" / "info" / "sparse-checkout"
        sparse_checkout_file.parent.mkdir(parents=True, exist_ok=True)
        sparse_checkout_file.write_text(sparse_path)

        # Add remote
        subprocess.run(
            ["git", "remote", "add", "origin", repo_url],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Fetch with depth and filter
        subprocess.run(
            ["git", "fetch", "--depth", "1", "--filter=blob:none", "origin", branch],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Checkout
        subprocess.run(
            ["git", "checkout", branch],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

    def _index_directory(
        self, directory: Path, base_path: Path, parser: RstDocumentParser | MarkdownDocumentParser
    ) -> int:
        """Index all supported files in a directory.

        Args:
            directory: Directory to scan for documentation files.
            base_path: Base path for calculating relative paths.
            parser: Parser instance to use.

        Returns:
            Number of documents indexed.
        """
        if not directory.exists():
            return 0

        extensions = parser.get_supported_extensions()
        count = 0

        for ext in extensions:
            for file_path in directory.rglob(f"*{ext}"):
                # Skip files in hidden directories
                if any(part.startswith(".") for part in file_path.parts):
                    continue

                doc = parser.parse_file(file_path, base_path)
                if doc:
                    self.db.upsert_document(doc)
                    count += 1

        return count
