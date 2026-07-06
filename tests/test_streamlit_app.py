from pathlib import Path

import duckdb
from streamlit.testing.v1 import AppTest

from research_lens.database import initialize_schema


def _dashboard_database(database_path: Path) -> None:
    connection = duckdb.connect(str(database_path))
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
            ("W2", "Second work", 2025, 20, False),
        ],
    )
    connection.execute(
        """
        INSERT INTO institutions (
            id,
            display_name,
            country_code,
            institution_type
        )
        VALUES ('I1', 'Example University', 'IN', 'education')
        """
    )
    connection.execute(
        """
        INSERT INTO work_author_institutions (
            work_id,
            author_id,
            institution_id
        )
        VALUES ('W1', 'A1', 'I1')
        """
    )
    connection.close()


def test_streamlit_app_loads_and_runs_a_baseline_question(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = tmp_path / "dashboard.duckdb"
    _dashboard_database(database_path)
    monkeypatch.setenv("DATABASE_PATH", str(database_path))
    monkeypatch.setenv("OLLAMA_BASE_URL", "")

    app_path = Path(__file__).parents[1] / "streamlit_app.py"
    app = AppTest.from_file(app_path, default_timeout=10).run()

    assert not app.exception
    assert app.title[0].value == "ResearchLens"
    assert [metric.value for metric in app.metric[:5]] == [
        "2",
        "0",
        "1",
        "0",
        "0",
    ]

    app.button(key="run_analysis").click().run()

    assert not app.exception
    assert not app.error
    assert len(app.dataframe) == 1
    assert "COUNT(DISTINCT wai.work_id)" in app.code[0].value

    app.button(key="clear_results").click().run()

    assert not app.exception
    assert len(app.dataframe) == 0
