import duckdb

from research_lens.analytics import METRICS
from research_lens.database import initialize_schema
from research_lens.schema import ALL_TABLES
from research_lens.sql_safety import validate_read_only_query


def _analytical_connection() -> duckdb.DuckDBPyConnection:
    connection = duckdb.connect(":memory:")
    initialize_schema(connection)

    connection.executemany(
        """
        INSERT INTO institutions (id, display_name)
        VALUES (?, ?)
        """,
        [
            ("I1", "Alpha University"),
            ("I2", "Beta Labs"),
        ],
    )
    connection.executemany(
        """
        INSERT INTO works (
            id,
            title,
            publication_year,
            cited_by_count,
            is_open_access
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            ("W1", "First work", 2024, 10, True),
            ("W2", "Second work", 2024, 30, False),
            ("W3", "Third work", 2025, 20, True),
        ],
    )
    connection.executemany(
        """
        INSERT INTO work_author_institutions (work_id, author_id, institution_id)
        VALUES (?, ?, ?)
        """,
        [
            ("W1", "A1", "I1"),
            ("W1", "A2", "I1"),
            ("W2", "A3", "I1"),
            ("W3", "A4", "I2"),
        ],
    )
    connection.executemany(
        """
        INSERT INTO topics (id, display_name)
        VALUES (?, ?)
        """,
        [
            ("T1", "Topic One"),
            ("T2", "Topic Two"),
        ],
    )
    connection.executemany(
        """
        INSERT INTO work_topics (work_id, topic_id, score, is_primary)
        VALUES (?, ?, ?, ?)
        """,
        [
            ("W1", "T1", 0.9, True),
            ("W1", "T2", 0.4, False),
            ("W2", "T1", 0.8, True),
            ("W3", "T2", 0.7, True),
        ],
    )
    return connection


def test_all_metrics_satisfy_the_read_only_policy() -> None:
    for metric in METRICS.values():
        validate_read_only_query(metric.sql, ALL_TABLES)


def test_institution_publications_counts_unique_works() -> None:
    connection = _analytical_connection()

    rows = connection.execute(METRICS["institution-publications"].sql).fetchall()

    assert rows == [("Alpha University", 2), ("Beta Labs", 1)]
    connection.close()


def test_open_access_by_year_calculates_percentage() -> None:
    connection = _analytical_connection()

    rows = connection.execute(METRICS["open-access-by-year"].sql).fetchall()

    assert [tuple(map(str, row)) for row in rows] == [
        ("2024", "2", "1", "50.0"),
        ("2025", "1", "1", "100.0"),
    ]
    connection.close()


def test_primary_topic_impact_aggregates_work_citations() -> None:
    connection = _analytical_connection()

    rows = connection.execute(METRICS["primary-topic-impact"].sql).fetchall()

    assert rows == [
        ("Topic One", 2, 20.0),
        ("Topic Two", 1, 20.0),
    ]
    connection.close()
