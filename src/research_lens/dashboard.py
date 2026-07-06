"""Read-only data helpers used by the ResearchLens dashboard."""

from __future__ import annotations

from pathlib import Path

from research_lens.database import connect_database
from research_lens.schema import CORE_TABLES


class DatabaseNotInitializedError(FileNotFoundError):
    """Raised when the configured ResearchLens database does not exist."""


def load_entity_counts(database_path: Path) -> dict[str, int]:
    """Return row counts for the core analytical entities."""

    if not database_path.exists():
        raise DatabaseNotInitializedError(
            f"Database not found at {database_path}. Run research-lens init-db first."
        )

    connection = connect_database(database_path, read_only=True)
    try:
        return {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in CORE_TABLES
        }
    finally:
        connection.close()
