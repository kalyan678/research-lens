from pathlib import Path

import pytest

from research_lens.agent import AgentResult
from research_lens.config import Settings
from research_lens.evaluation import EvaluationQuestion, evaluate_question, run_evaluation
from research_lens.query_service import QuestionRejectedError, QuestionResponse


def _settings(database_path: Path) -> Settings:
    return Settings(
        database_path=database_path,
        openalex_api_key=None,
        ollama_base_url=None,
        ollama_model="qwen2.5-coder:3b",
        ollama_timeout_seconds=10,
    )


def _question() -> EvaluationQuestion:
    return EvaluationQuestion(
        id="sample-01",
        category="sample",
        question="Show publication counts by institution",
        expected_column_groups=(
            ("institution", "display_name"),
            ("publication_count", "publications"),
        ),
        min_rows=1,
    )


def test_evaluate_question_passes_when_columns_and_rows_match(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fake_answer_question(
        settings: Settings,
        question: str,
        provider: str,
        *,
        max_rows: int,
    ) -> QuestionResponse:
        return QuestionResponse(
            provider_label="fake",
            result=AgentResult(
                question=question,
                sql="SELECT 'Stanford University' AS institution, 5 AS publication_count",
                columns=["institution", "publication_count"],
                rows=[("Stanford University", 5)],
                attempts=1,
            ),
        )

    monkeypatch.setattr("research_lens.evaluation.answer_question", fake_answer_question)

    result = evaluate_question(_settings(tmp_path / "unused.duckdb"), _question(), "baseline")

    assert result.passed is True
    assert result.row_count == 1
    assert result.attempts == 1
    assert result.reason == "Passed"


def test_evaluate_question_fails_when_expected_columns_are_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fake_answer_question(
        settings: Settings,
        question: str,
        provider: str,
        *,
        max_rows: int,
    ) -> QuestionResponse:
        return QuestionResponse(
            provider_label="fake",
            result=AgentResult(
                question=question,
                sql="SELECT 5 AS count",
                columns=["count"],
                rows=[(5,)],
                attempts=1,
            ),
        )

    monkeypatch.setattr("research_lens.evaluation.answer_question", fake_answer_question)

    result = evaluate_question(_settings(tmp_path / "unused.duckdb"), _question(), "baseline")

    assert result.passed is False
    assert "Missing expected column group" in result.reason


def test_evaluate_question_records_rejected_questions(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fake_answer_question(
        settings: Settings,
        question: str,
        provider: str,
        *,
        max_rows: int,
    ) -> QuestionResponse:
        raise QuestionRejectedError("unsupported question")

    monkeypatch.setattr("research_lens.evaluation.answer_question", fake_answer_question)

    result = evaluate_question(_settings(tmp_path / "unused.duckdb"), _question(), "baseline")

    assert result.passed is False
    assert result.row_count == 0
    assert result.attempts is None
    assert result.reason == "unsupported question"


def test_run_evaluation_filters_questions_by_provider(tmp_path: Path) -> None:
    questions = (
        EvaluationQuestion(
            id="baseline-01",
            category="sample",
            question="baseline question",
            expected_column_groups=(("publication_count",),),
            min_rows=1,
            providers=("baseline",),
        ),
        EvaluationQuestion(
            id="ollama-01",
            category="sample",
            question="ollama question",
            expected_column_groups=(("publication_count",),),
            min_rows=1,
            providers=("ollama",),
        ),
    )

    results = run_evaluation(
        _settings(tmp_path / "unused.duckdb"),
        "ollama",
        questions=questions,
    )

    assert [result.question_id for result in results] == ["ollama-01"]
