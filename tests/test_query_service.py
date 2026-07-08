from pathlib import Path

import duckdb
import pytest

from research_lens.config import Settings
from research_lens.database import initialize_schema
from research_lens.query_service import QuestionRejectedError, answer_question


def _settings(database_path: Path, *, ollama_base_url: str | None = None) -> Settings:
    return Settings(
        database_path=database_path,
        openalex_api_key=None,
        ollama_base_url=ollama_base_url,
        ollama_model="qwen2.5-coder:3b",
        ollama_timeout_seconds=10,
    )


def _database_with_works(database_path: Path) -> None:
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
    connection.close()


def test_answer_question_uses_the_deterministic_baseline(tmp_path: Path) -> None:
    database_path = tmp_path / "research_lens.duckdb"
    _database_with_works(database_path)

    response = answer_question(
        _settings(database_path),
        "What is the open access percentage by year?",
        "baseline",
    )

    assert response.provider_label == "Deterministic baseline"
    assert response.result.columns == [
        "publication_year",
        "total_publications",
        "open_access_publications",
        "open_access_percentage",
    ]
    assert response.result.rows == [
        (2024, 1, 1, 100.0),
        (2025, 1, 0, 0.0),
    ]


def test_answer_question_uses_hybrid_baseline_fast_path_without_ollama(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "research_lens.duckdb"
    _database_with_works(database_path)

    response = answer_question(
        _settings(database_path),
        "What is the open access percentage by year?",
        "hybrid",
    )

    assert response.provider_label == "Hybrid (baseline fast path)"
    assert response.result.columns == [
        "publication_year",
        "total_publications",
        "open_access_publications",
        "open_access_percentage",
    ]


def test_answer_question_explains_missing_hybrid_ollama_fallback(
    tmp_path: Path,
) -> None:
    with pytest.raises(QuestionRejectedError, match="outside the baseline"):
        answer_question(
            _settings(tmp_path / "unused.duckdb"),
            "Who wrote the earliest paper?",
            "hybrid",
        )


def test_answer_question_explains_missing_ollama_configuration(
    tmp_path: Path,
) -> None:
    with pytest.raises(QuestionRejectedError, match="OLLAMA_BASE_URL"):
        answer_question(
            _settings(tmp_path / "unused.duckdb"),
            "List every work",
            "ollama",
        )


def test_answer_question_rejects_an_unknown_provider(tmp_path: Path) -> None:
    with pytest.raises(QuestionRejectedError, match="Unsupported provider"):
        answer_question(
            _settings(tmp_path / "unused.duckdb"),
            "List every work",
            "unsupported",  # type: ignore[arg-type]
        )
