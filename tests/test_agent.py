from pathlib import Path

import duckdb
import pytest

from research_lens.agent import build_sql_prompt, extract_sql, run_sql_agent
from research_lens.database import initialize_schema
from research_lens.sql_safety import UnsafeQueryError


def test_extract_sql_strips_surrounding_whitespace() -> None:
    response = "  SELECT id, title FROM works;  \n"

    assert extract_sql(response) == "SELECT id, title FROM works;"


def test_extract_sql_removes_markdown_fence() -> None:
    response = """```sql
SELECT publication_year, COUNT(*) FROM works GROUP BY publication_year;
```"""

    assert extract_sql(response) == (
        "SELECT publication_year, COUNT(*) FROM works GROUP BY publication_year;"
    )


def test_build_sql_prompt_contains_question_schema_and_rules() -> None:
    prompt = build_sql_prompt("Which institutions have the most publications?")

    assert "Which institutions have the most publications?" in prompt
    assert "institutions.id = work_author_institutions.institution_id" in prompt
    assert "COUNT(DISTINCT work_id)" in prompt
    assert "Return exactly one read-only SELECT query" in prompt


def test_build_sql_prompt_rejects_empty_question() -> None:
    with pytest.raises(ValueError, match="Question cannot be empty"):
        build_sql_prompt("   ")


def _agent_database(path: Path) -> None:
    connection = duckdb.connect(str(path))
    initialize_schema(connection)
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
            ("W2", "Second work", 2024, 20, False),
            ("W3", "Third work", 2025, 30, True),
        ],
    )
    connection.close()


def test_run_sql_agent_executes_a_fenced_model_query(tmp_path: Path) -> None:
    database_path = tmp_path / "agent.duckdb"
    _agent_database(database_path)

    def fake_generator(prompt: str) -> str:
        assert "How many publications are there by year?" in prompt
        return """```sql
SELECT publication_year, COUNT(*) AS publications
FROM works
GROUP BY publication_year
ORDER BY publication_year
```"""

    result = run_sql_agent(
        "  How many publications are there by year?  ",
        fake_generator,
        database_path,
    )

    assert result.question == "How many publications are there by year?"
    assert result.columns == ["publication_year", "publications"]
    assert result.rows == [(2024, 2), (2025, 1)]
    assert "SELECT publication_year" in result.sql


def test_run_sql_agent_rejects_unsafe_model_query(tmp_path: Path) -> None:
    database_path = tmp_path / "agent.duckdb"
    _agent_database(database_path)

    with pytest.raises(UnsafeQueryError, match="Only SELECT queries are allowed"):
        run_sql_agent(
            "Delete every work",
            lambda _prompt: "DELETE FROM works",
            database_path,
        )


def test_run_sql_agent_rejects_invalid_row_limit(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="max_rows must be between 1 and 1000"):
        run_sql_agent(
            "List works",
            lambda _prompt: "SELECT * FROM works",
            tmp_path / "unused.duckdb",
            max_rows=0,
        )
