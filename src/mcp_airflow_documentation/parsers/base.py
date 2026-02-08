"""Base parser interface for documentation."""

from abc import ABC, abstractmethod
from pathlib import Path

from mcp_airflow_documentation.models import Document


class DocumentParser(ABC):
    """Abstract base class for document parsers."""

    def __init__(self, source: str, base_url: str) -> None:
        """Initialise parser with source identifier and base URL.

        Args:
            source: Source identifier ('airflow-core' or 'airflow-python-client').
            base_url: Base URL for generating documentation links.
        """
        self.source = source
        self.base_url = base_url

    @abstractmethod
    def parse_file(self, file_path: Path, base_path: Path) -> Document | None:
        """Parse a documentation file.

        Args:
            file_path: Absolute path to the file to parse.
            base_path: Base directory path for calculating relative paths.

        Returns:
            Document instance or None if parsing fails.
        """
        pass

    @abstractmethod
    def get_supported_extensions(self) -> list[str]:
        """Return list of supported file extensions.

        Returns:
            List of file extensions (e.g., ['.rst', '.md']).
        """
        pass

    def _get_relative_path(self, file_path: Path, base_path: Path) -> str:
        """Calculate relative path from base path.

        Args:
            file_path: Absolute path to the file.
            base_path: Base directory path.

        Returns:
            Relative path as string.
        """
        return str(file_path.relative_to(base_path))

    def _extract_section_from_path(self, relative_path: str) -> str:
        """Extract section name from file path.

        Args:
            relative_path: Relative path to the file.

        Returns:
            Section name derived from the directory structure.
        """
        parts = Path(relative_path).parts
        if len(parts) > 1:
            # Use the first directory as section
            section = parts[0].replace("-", " ").replace("_", " ").title()
            return section
        return "Root"
