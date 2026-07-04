from __future__ import annotations

from typing import Any

import duckdb

from research_lens.normalization import NormalizedBundle


def _upsert(
    connection: duckdb.DuckDBPyConnection,
    table: str,
    rows: list[dict[str, Any]],
    conflict_columns: list[str],
    update_columns: list[str],
) -> None:
    if not rows:
        return

    columns = list(rows[0])
    column_list = ", ".join(columns)
    placeholders = ", ".join("?" for _ in columns)
    conflict_target = ", ".join(conflict_columns)

    if update_columns:
        assignments = ", ".join(
            f"{column} = EXCLUDED.{column}" for column in update_columns
        )
        conflict_action = f"DO UPDATE SET {assignments}"
    else:
        conflict_action = "DO NOTHING"

    statement = f"""
        INSERT INTO {table} ({column_list})
        VALUES ({placeholders})
        ON CONFLICT ({conflict_target}) {conflict_action}
    """
    parameters = [[row.get(column) for column in columns] for row in rows]
    connection.executemany(statement, parameters)


class ResearchRepository:
    def __init__(self, connection: duckdb.DuckDBPyConnection) -> None:
        self.connection = connection

    def upsert_work_bundle(self, bundle: NormalizedBundle) -> None:
        _upsert(
            self.connection,
            "sources",
            bundle["sources"],
            ["id"],
            ["display_name", "source_type", "issn_l", "host_organization"],
        )
        _upsert(
            self.connection,
            "institutions",
            bundle["institutions"],
            ["id"],
            ["display_name", "country_code", "institution_type"],
        )
        _upsert(
            self.connection,
            "authors",
            bundle["authors"],
            ["id"],
            ["display_name", "orcid"],
        )
        _upsert(
            self.connection,
            "topics",
            bundle["topics"],
            ["id"],
            ["display_name", "domain_name", "field_name", "subfield_name"],
        )
        _upsert(
            self.connection,
            "works",
            bundle["works"],
            ["id"],
            [
                "doi",
                "title",
                "publication_year",
                "publication_date",
                "work_type",
                "language",
                "cited_by_count",
                "is_open_access",
                "open_access_status",
                "source_id",
                "openalex_updated_date",
            ],
        )
        _upsert(
            self.connection,
            "work_authors",
            bundle["work_authors"],
            ["work_id", "author_id"],
            ["author_position", "is_corresponding"],
        )
        _upsert(
            self.connection,
            "work_author_institutions",
            bundle["work_author_institutions"],
            ["work_id", "author_id", "institution_id"],
            [],
        )
        _upsert(
            self.connection,
            "work_topics",
            bundle["work_topics"],
            ["work_id", "topic_id"],
            ["score", "is_primary"],
        )
