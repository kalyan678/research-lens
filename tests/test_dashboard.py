from pathlib import Path

import duckdb
import pytest

from research_lens.dashboard import (
    DatabaseNotInitializedError,
    load_entity_counts,
)
from research_lens.database import initialize_schema


def test_load_entity_counts_reads_the_core_tables(tmp_path: Path) -> None:
    database_path = tmp_path / "dashboard.duckdb"
    connection = duckdb.connect(str(database_path))
    initialize_schema(connection)
    connection.execute(
        """
        INSERT INTO works (
            id,
            title,
            cited_by_count,
            is_open_access
        )
        VALUES ('W1', 'Example work', 0, FALSE)
        """
    )
    connection.close()

    counts = load_entity_counts(database_path)

    assert counts == {
        "works": 1,
        "authors": 0,
        "institutions": 0,
        "topics": 0,
        "sources": 0,
    }


def test_load_entity_counts_requires_an_initialized_database(
    tmp_path: Path,
) -> None:
    with pytest.raises(DatabaseNotInitializedError, match="init-db"):
        load_entity_counts(tmp_path / "missing.duckdb")
