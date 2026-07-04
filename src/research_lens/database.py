from __future__ import annotations

from pathlib import Path

import duckdb

from research_lens.schema import SCHEMA_STATEMENTS


def connect_database(
    database_path: Path,
    *,
    read_only: bool = False,
) -> duckdb.DuckDBPyConnection:
    if not read_only:
        database_path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(database_path), read_only=read_only)


def initialize_schema(connection: duckdb.DuckDBPyConnection) -> None:
    for statement in SCHEMA_STATEMENTS:
        connection.execute(statement)


def database_is_reachable(connection: duckdb.DuckDBPyConnection) -> bool:
    return connection.execute("SELECT 1").fetchone() == (1,)
