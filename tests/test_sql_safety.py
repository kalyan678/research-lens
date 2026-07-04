import pytest

from research_lens.schema import ALL_TABLES
from research_lens.sql_safety import UnsafeQueryError, validate_read_only_query


def test_accepts_select_with_join_and_cte() -> None:
    sql = """
        WITH productive_institutions AS (
            SELECT institution_id, COUNT(DISTINCT work_id) AS works
            FROM work_author_institutions
            GROUP BY institution_id
        )
        SELECT i.display_name, p.works
        FROM productive_institutions p
        JOIN institutions i ON i.id = p.institution_id
        ORDER BY p.works DESC
    """

    validated = validate_read_only_query(sql, ALL_TABLES)

    assert "productive_institutions" in validated
    assert "JOIN institutions" in validated


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM works",
        "DROP TABLE works",
        "UPDATE works SET title = 'changed'",
        "SELECT * FROM works; SELECT * FROM authors",
        "SELECT * FROM read_csv_auto('private.csv')",
        "SELECT * FROM unrelated_table",
    ],
)
def test_rejects_unsafe_or_unknown_queries(sql: str) -> None:
    with pytest.raises(UnsafeQueryError):
        validate_read_only_query(sql, ALL_TABLES)

