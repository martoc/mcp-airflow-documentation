"""Data models for Airflow documentation."""

from dataclasses import dataclass


@dataclass
class Document:
    """Represents a documentation page from either Airflow core or Python client."""

    source: str  # 'airflow-core' or 'airflow-python-client'
    path: str
    title: str
    description: str | None
    section: str
    content: str
    url: str

    def __post_init__(self) -> None:
        """Validate source field."""
        if self.source not in ("airflow-core", "airflow-python-client"):
            raise ValueError(
                f"Invalid source: {self.source}. "
                "Must be 'airflow-core' or 'airflow-python-client'"
            )


@dataclass
class SearchResult:
    """Represents a search result from the documentation database."""

    source: str  # 'airflow-core' or 'airflow-python-client'
    path: str
    title: str
    url: str
    snippet: str
    score: float
    section: str

    def format(self) -> str:
        """Format search result for display."""
        source_display = {
            "airflow-core": "Airflow Core",
            "airflow-python-client": "Python Client",
        }.get(self.source, self.source)

        return (
            f"**{self.title}** ({source_display})\n"
            f"Section: {self.section}\n"
            f"Score: {self.score:.2f}\n"
            f"URL: {self.url}\n\n"
            f"{self.snippet}\n"
        )
