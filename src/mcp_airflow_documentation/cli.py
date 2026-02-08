"""Command-line interface for indexing Airflow documentation."""

import sys
from pathlib import Path

import click

from mcp_airflow_documentation.database import DocumentDatabase
from mcp_airflow_documentation.indexer import AirflowDocsIndexer


def get_default_db_path() -> Path:
    """Get the default database path.

    Returns:
        Path to the database file in the data directory.
    """
    # Use data directory relative to package
    package_dir = Path(__file__).parent.parent.parent
    data_dir = package_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "airflow-docs.db"


@click.group()
def cli() -> None:
    """Airflow documentation indexer CLI."""
    pass


@cli.command()
@click.option(
    "--source",
    type=click.Choice(["airflow-core", "airflow-python-client"]),
    help="Index only specific source",
)
@click.option("--branch", default="main", help="Git branch to index (default: main)")
@click.option("--rebuild", is_flag=True, help="Clear existing documents before indexing")
@click.option("--db-path", type=click.Path(), help="Database path (optional)")
def index(source: str | None, branch: str, rebuild: bool, db_path: str | None) -> None:
    """Index Airflow documentation from GitHub repositories."""
    db_file = Path(db_path) if db_path else get_default_db_path()
    db = DocumentDatabase(db_file)
    indexer = AirflowDocsIndexer(db)

    click.echo(f"Using database: {db_file}")

    if rebuild:
        click.echo("Rebuilding index (clearing existing documents)...")

    if source:
        click.echo(f"Indexing {source} from branch '{branch}'...")
        count = indexer.index_source(source, branch=branch, rebuild=rebuild)
        click.echo(f"✓ Indexed {count} documents from {source}")
    else:
        click.echo(f"Indexing all sources from branch '{branch}'...")
        results = indexer.index_all_sources(branch=branch, rebuild=rebuild)
        click.echo(f"✓ Indexed {results['airflow-core']} documents from airflow-core")
        click.echo(
            f"✓ Indexed {results['airflow-python-client']} documents from airflow-python-client"
        )
        click.echo(f"✓ Total: {results['total']} documents")

    # Show final statistics
    stats = db.get_stats()
    click.echo("\nDatabase statistics:")
    click.echo(f"  Airflow Core: {stats['airflow-core']} documents")
    click.echo(f"  Python Client: {stats['airflow-python-client']} documents")
    click.echo(f"  Total: {stats['total']} documents")


@cli.command()
@click.option("--db-path", type=click.Path(), help="Database path (optional)")
def stats(db_path: str | None) -> None:
    """Show database statistics."""
    db_file = Path(db_path) if db_path else get_default_db_path()

    if not db_file.exists():
        click.echo(f"Database not found: {db_file}", err=True)
        click.echo("Run 'airflow-docs-index index' to create the database.")
        sys.exit(1)

    db = DocumentDatabase(db_file)
    stats_data = db.get_stats()

    click.echo(f"Database: {db_file}")
    click.echo("\nDocument counts:")
    click.echo(f"  Airflow Core: {stats_data['airflow-core']}")
    click.echo(f"  Python Client: {stats_data['airflow-python-client']}")
    click.echo(f"  Total: {stats_data['total']}")

    # Show sections
    click.echo("\nSections (Airflow Core):")
    core_sections = db.get_sections(source="airflow-core")
    if core_sections:
        for section in core_sections[:10]:  # Show first 10
            click.echo(f"  - {section}")
        if len(core_sections) > 10:
            click.echo(f"  ... and {len(core_sections) - 10} more")
    else:
        click.echo("  (none)")

    click.echo("\nSections (Python Client):")
    client_sections = db.get_sections(source="airflow-python-client")
    if client_sections:
        for section in client_sections[:10]:  # Show first 10
            click.echo(f"  - {section}")
        if len(client_sections) > 10:
            click.echo(f"  ... and {len(client_sections) - 10} more")
    else:
        click.echo("  (none)")


@cli.command()
@click.option("--db-path", type=click.Path(), help="Database path (optional)")
@click.confirmation_option(prompt="Are you sure you want to clear the database?")
def clear(db_path: str | None) -> None:
    """Clear all documents from the database."""
    db_file = Path(db_path) if db_path else get_default_db_path()

    if not db_file.exists():
        click.echo(f"Database not found: {db_file}", err=True)
        sys.exit(1)

    db = DocumentDatabase(db_file)
    db.clear()
    click.echo("✓ Database cleared")


def main() -> None:
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
