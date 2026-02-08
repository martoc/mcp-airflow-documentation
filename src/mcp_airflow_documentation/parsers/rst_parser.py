"""Parser for Airflow RST documentation files."""

import re
from pathlib import Path

import docutils.frontend  # type: ignore[import-untyped]
import docutils.nodes  # type: ignore[import-untyped]
import docutils.parsers.rst  # type: ignore[import-untyped]
import docutils.utils  # type: ignore[import-untyped]

from mcp_airflow_documentation.models import Document
from mcp_airflow_documentation.parsers.base import DocumentParser


class MetadataVisitor(docutils.nodes.GenericNodeVisitor):  # type: ignore[misc]
    """Visitor to extract metadata from RST document tree."""

    def __init__(self, document: docutils.nodes.document) -> None:
        """Initialise metadata visitor.

        Args:
            document: Docutils document tree.
        """
        super().__init__(document)
        self.title: str | None = None
        self.description: str | None = None
        self._in_docinfo = False

    def visit_title(self, node: docutils.nodes.title) -> None:
        """Visit title node (first section header).

        Args:
            node: Title node.
        """
        if self.title is None:
            self.title = node.astext()

    def visit_paragraph(self, node: docutils.nodes.paragraph) -> None:
        """Visit paragraph node (extract first as description).

        Args:
            node: Paragraph node.
        """
        if self.description is None and not self._in_docinfo:
            self.description = node.astext()

    def visit_docinfo(self, node: docutils.nodes.docinfo) -> None:
        """Visit docinfo node.

        Args:
            node: Docinfo node.
        """
        self._in_docinfo = True

    def depart_docinfo(self, node: docutils.nodes.docinfo) -> None:
        """Depart docinfo node.

        Args:
            node: Docinfo node.
        """
        self._in_docinfo = False

    def default_visit(self, node: docutils.nodes.Node) -> None:
        """Default visit handler (no-op).

        Args:
            node: Any node.
        """

    def default_departure(self, node: docutils.nodes.Node) -> None:
        """Default departure handler (no-op).

        Args:
            node: Any node.
        """


class TextContentVisitor(docutils.nodes.GenericNodeVisitor):  # type: ignore[misc]
    """Visitor to extract searchable text content from RST document tree."""

    def __init__(self, document: docutils.nodes.document) -> None:
        """Initialise text content visitor.

        Args:
            document: Docutils document tree.
        """
        super().__init__(document)
        self._text_parts: list[str] = []
        self._skip_depth = 0

    def visit_literal_block(self, node: docutils.nodes.literal_block) -> None:
        """Skip code blocks.

        Args:
            node: Literal block node.

        Raises:
            docutils.nodes.SkipNode: Always raised to skip code blocks.
        """
        raise docutils.nodes.SkipNode

    def visit_comment(self, node: docutils.nodes.comment) -> None:
        """Skip comments.

        Args:
            node: Comment node.

        Raises:
            docutils.nodes.SkipNode: Always raised to skip comments.
        """
        raise docutils.nodes.SkipNode

    def visit_Text(self, node: docutils.nodes.Text) -> None:  # noqa: N802
        """Visit text node and collect content.

        Args:
            node: Text node.
        """
        if self._skip_depth == 0:
            text = node.astext().strip()
            if text:
                self._text_parts.append(text)

    def default_visit(self, node: docutils.nodes.Node) -> None:
        """Default visit handler (no-op).

        Args:
            node: Any node.
        """

    def default_departure(self, node: docutils.nodes.Node) -> None:
        """Default departure handler (no-op).

        Args:
            node: Any node.
        """

    def get_text(self) -> str:
        """Get collected text content.

        Returns:
            Concatenated text content.
        """
        return " ".join(self._text_parts)


class RstDocumentParser(DocumentParser):
    """Parser for RST documentation files."""

    def __init__(self, source: str, base_url: str) -> None:
        """Initialise RST parser.

        Args:
            source: Source identifier ('airflow-core').
            base_url: Base URL for generating documentation links.
        """
        super().__init__(source, base_url)

    def get_supported_extensions(self) -> list[str]:
        """Return list of supported file extensions.

        Returns:
            List of RST file extensions.
        """
        return [".rst", ".rest"]

    def parse_file(self, file_path: Path, base_path: Path) -> Document | None:
        """Parse an RST file and extract metadata and content.

        Args:
            file_path: Path to the RST file.
            base_path: Base path of the documentation directory.

        Returns:
            Document instance or None if parsing fails.
        """
        try:
            source_text = file_path.read_text(encoding="utf-8")
            doctree = self._parse_rst(source_text, file_path)
            relative_path = self._get_relative_path(file_path, base_path)
            title = self._extract_title(doctree, file_path)
            description = self._extract_description(doctree)
            section = self._extract_section_from_path(relative_path)
            content = self._extract_text_content(doctree)
            content = self._clean_content(content)
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

    def _parse_rst(self, source: str, file_path: Path) -> docutils.nodes.document:
        """Parse RST source into docutils document tree.

        Args:
            source: RST source text.
            file_path: Path to the file (for error reporting).

        Returns:
            Docutils document tree.
        """
        parser = docutils.parsers.rst.Parser()
        components = (docutils.parsers.rst.Parser,)
        settings = docutils.frontend.OptionParser(components=components).get_default_values()
        settings.report_level = 5  # Suppress warnings
        document = docutils.utils.new_document(str(file_path), settings)
        parser.parse(source, document)
        return document

    def _extract_title(self, doctree: docutils.nodes.document, file_path: Path) -> str:
        """Extract title from RST document tree.

        Args:
            doctree: Docutils document tree.
            file_path: Path to the file for fallback title extraction.

        Returns:
            Document title.
        """
        visitor = MetadataVisitor(doctree)
        doctree.walk(visitor)

        if visitor.title:
            return visitor.title

        # Fallback to filename if no title found
        return file_path.stem.replace("-", " ").replace("_", " ").title()

    def _extract_description(self, doctree: docutils.nodes.document) -> str | None:
        """Extract description from RST document tree.

        Args:
            doctree: Docutils document tree.

        Returns:
            Document description or None.
        """
        visitor = MetadataVisitor(doctree)
        doctree.walk(visitor)
        return visitor.description

    def _extract_text_content(self, doctree: docutils.nodes.document) -> str:
        """Extract searchable text content from RST document tree.

        Args:
            doctree: Docutils document tree.

        Returns:
            Extracted text content.
        """
        visitor = TextContentVisitor(doctree)
        doctree.walk(visitor)
        return visitor.get_text()

    def _clean_content(self, content: str) -> str:
        """Clean RST content for indexing.

        Removes RST directives, roles, and other markup artifacts.

        Args:
            content: Raw RST content.

        Returns:
            Cleaned content suitable for indexing.
        """
        # Remove RST directives (.. directive::)
        content = re.sub(r"\.\.\s+\w+::[^\n]*\n(?:\s+[^\n]+\n)*", "", content)
        # Clean RST roles (:role:`text` -> text)
        content = re.sub(r":\w+:`([^`]+)`", r"\1", content)
        # Remove RST comments
        content = re.sub(r"\.\.\s+[^\n]+\n(?:\s+[^\n]+\n)*", "", content)
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
        # Convert .rst to .html
        path_str = re.sub(r"\.(rst|rest)$", ".html", relative_path)
        return f"{self.base_url}/{path_str}"
