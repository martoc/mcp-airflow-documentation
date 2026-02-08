"""Parser for Airflow Markdown documentation files."""

import re
from pathlib import Path

import frontmatter  # type: ignore[import-untyped]

from mcp_airflow_documentation.models import Document
from mcp_airflow_documentation.parsers.base import DocumentParser


class MarkdownDocumentParser(DocumentParser):
    """Parser for Markdown documentation files with YAML frontmatter."""

    def __init__(self, source: str, base_url: str) -> None:
        """Initialise Markdown parser.

        Args:
            source: Source identifier ('airflow-python-client').
            base_url: Base URL for generating documentation links.
        """
        super().__init__(source, base_url)

    def get_supported_extensions(self) -> list[str]:
        """Return list of supported file extensions.

        Returns:
            List of Markdown file extensions.
        """
        return [".md", ".markdown"]

    def parse_file(self, file_path: Path, base_path: Path) -> Document | None:
        """Parse a markdown file and extract metadata and content.

        Args:
            file_path: Path to the markdown file.
            base_path: Base path of the documentation directory.

        Returns:
            Document instance or None if parsing fails.
        """
        try:
            post = frontmatter.load(file_path)
            relative_path = self._get_relative_path(file_path, base_path)
            title = self._extract_title(post.metadata, file_path)
            description = self._extract_description(post.metadata)
            section = self._extract_section_from_path(relative_path)
            content = self._clean_content(post.content)
            url = self._compute_url(relative_path)

            return Document(
                source=self.source,
                path=relative_path,
                title=title,
                description=description,
                section=section,
                content=content,
                url=url,
            )
        except Exception:
            return None

    def _extract_title(self, metadata: dict[str, object], file_path: Path) -> str:
        """Extract title from frontmatter.

        Args:
            metadata: Dictionary of frontmatter fields.
            file_path: Path to the file for fallback title extraction.

        Returns:
            Document title.
        """
        title = metadata.get("title")
        if isinstance(title, str):
            return title

        # Fallback to filename if no title in frontmatter
        return file_path.stem.replace("-", " ").replace("_", " ").title()

    def _extract_description(self, metadata: dict[str, object]) -> str | None:
        """Extract description from frontmatter.

        Args:
            metadata: Dictionary of frontmatter fields.

        Returns:
            Document description or None.
        """
        description = metadata.get("description")
        if isinstance(description, str):
            return description
        return None

    def _clean_content(self, content: str) -> str:
        """Clean markdown content for indexing.

        Removes Jekyll-specific syntax and other markup artifacts.

        Args:
            content: Raw markdown content.

        Returns:
            Cleaned content suitable for indexing.
        """
        # Remove Jekyll liquid tags
        content = re.sub(r"\{%.*?%\}", "", content)
        content = re.sub(r"\{\{.*?\}\}", "", content)
        # Remove HTML comments
        content = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL)
        # Remove HTML tags
        content = re.sub(r"<[^>]+>", "", content)
        # Remove markdown links but keep text [text](url) -> text
        content = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", content)
        # Remove markdown images ![alt](url) -> alt
        content = re.sub(r"!\[([^\]]*)\]\([^\)]+\)", r"\1", content)
        # Remove markdown code blocks
        content = re.sub(r"```.*?```", "", content, flags=re.DOTALL)
        content = re.sub(r"`[^`]+`", "", content)
        # Remove markdown headers #
        content = re.sub(r"^#+\s+", "", content, flags=re.MULTILINE)
        # Remove multiple whitespace
        content = re.sub(r"\s+", " ", content)
        return content.strip()

    def _compute_url(self, relative_path: str) -> str:
        """Compute the documentation URL.

        Args:
            relative_path: Path relative to docs directory.

        Returns:
            Full URL to the documentation page.
        """
        # Convert .md to .html
        path_str = re.sub(r"\.(md|markdown)$", ".html", relative_path)
        return f"{self.base_url}/{path_str}"
