"""Evaluation harness for ResearchLens natural-language questions."""

from __future__ import annotations

import time
from dataclasses import dataclass

from research_lens.config import Settings
from research_lens.query_service import Provider, QuestionRejectedError, answer_question


@dataclass(frozen=True)
class EvaluationQuestion:
    id: str
    category: str
    question: str
    expected_column_groups: tuple[tuple[str, ...], ...]
    min_rows: int
    providers: tuple[Provider, ...] = ("baseline", "ollama")


@dataclass(frozen=True)
class EvaluationResult:
    question_id: str
    category: str
    passed: bool
    row_count: int
    attempts: int | None
    duration_seconds: float
    reason: str


EVALUATION_QUESTIONS: tuple[EvaluationQuestion, ...] = (
    EvaluationQuestion(
        id="institution-ranking-01",
        category="institution ranking",
        question=(
            "Show the top 10 institutions ranked by number of unique publications, "
            "including each publication count."
        ),
        expected_column_groups=(
            ("institution", "display_name", "institution_name"),
            (
                "publication_count",
                "publications",
                "unique_publications",
                "work_count",
                "paper_count",
                "papers",
                "num_publications",
                "number_of_publications",
                "num_papers",
                "total_publications",
            ),
        ),
        min_rows=5,
    ),
    EvaluationQuestion(
        id="institution-ranking-02",
        category="institution ranking",
        question="Which universities or institutions published the most papers?",
        expected_column_groups=(
            ("institution", "display_name", "institution_name"),
            (
                "publication_count",
                "publications",
                "unique_publications",
                "work_count",
                "paper_count",
                "papers",
                "num_publications",
                "number_of_publications",
                "num_papers",
                "total_publications",
            ),
        ),
        min_rows=5,
    ),
    EvaluationQuestion(
        id="open-access-01",
        category="open access trend",
        question=(
            "For each publication year, show total publications, open access "
            "publications, and the open access percentage."
        ),
        expected_column_groups=(
            ("publication_year", "year"),
            ("total_publications", "publications", "publication_count"),
            ("open_access_publications", "open_access_count"),
            ("open_access_percentage", "open_access_percent", "percentage"),
        ),
        min_rows=2,
    ),
    EvaluationQuestion(
        id="open-access-02",
        category="open access trend",
        question="Compare the open access rate by publication year.",
        expected_column_groups=(
            ("publication_year", "year"),
            ("open_access_percentage", "open_access_percent", "percentage"),
        ),
        min_rows=2,
    ),
    EvaluationQuestion(
        id="topic-impact-01",
        category="topic impact",
        question=(
            "For each primary topic, show its unique publication count and average "
            "citations, ranked by publication count and then average citations descending."
        ),
        expected_column_groups=(
            ("topic", "topic_name", "display_name", "primary_topic", "primary_topic_name"),
            ("publication_count", "publications", "unique_publications"),
            (
                "average_citations",
                "avg_citations",
                "avg_citation_count",
                "avg_cited_by_count",
                "average_citation_count",
                "citation_impact",
            ),
        ),
        min_rows=5,
    ),
    EvaluationQuestion(
        id="topic-impact-02",
        category="topic impact",
        question="Which primary topics have the highest research impact by citations?",
        expected_column_groups=(
            ("topic", "topic_name", "display_name", "primary_topic", "primary_topic_name"),
            (
                "average_citations",
                "avg_citations",
                "avg_citation_count",
                "avg_cited_by_count",
                "average_citation_count",
                "citation_impact",
            ),
        ),
        min_rows=5,
    ),
    EvaluationQuestion(
        id="paper-affiliations-01",
        category="paper affiliation detail",
        question=(
            "List each author and institution for the paper titled 'Bias and Fairness "
            "in Large Language Models: A Survey', ordered by institution and author."
        ),
        expected_column_groups=(
            ("author", "author_name", "display_name"),
            ("institution", "institution_name"),
        ),
        min_rows=1,
        providers=("ollama",),
    ),
)


def _normalize_column_name(column: str) -> str:
    return column.strip().lower()


def _missing_column_groups(
    columns: list[str],
    expected_column_groups: tuple[tuple[str, ...], ...],
) -> list[tuple[str, ...]]:
    normalized_columns = {_normalize_column_name(column) for column in columns}
    return [
        group
        for group in expected_column_groups
        if normalized_columns.isdisjoint({_normalize_column_name(column) for column in group})
    ]


def evaluate_question(
    settings: Settings,
    evaluation_question: EvaluationQuestion,
    provider: Provider,
    *,
    max_rows: int = 20,
) -> EvaluationResult:
    started_at = time.perf_counter()
    try:
        response = answer_question(
            settings,
            evaluation_question.question,
            provider,
            max_rows=max_rows,
        )
    except QuestionRejectedError as error:
        return EvaluationResult(
            question_id=evaluation_question.id,
            category=evaluation_question.category,
            passed=False,
            row_count=0,
            attempts=None,
            duration_seconds=time.perf_counter() - started_at,
            reason=str(error),
        )

    result = response.result
    missing_groups = _missing_column_groups(
        result.columns,
        evaluation_question.expected_column_groups,
    )
    if missing_groups:
        missing = "; ".join(" or ".join(group) for group in missing_groups)
        passed = False
        observed = ", ".join(result.columns)
        reason = f"Missing expected column group(s): {missing}. Observed: {observed}"
    elif len(result.rows) < evaluation_question.min_rows:
        passed = False
        reason = (
            f"Expected at least {evaluation_question.min_rows} row(s), "
            f"received {len(result.rows)}"
        )
    else:
        passed = True
        reason = "Passed"

    return EvaluationResult(
        question_id=evaluation_question.id,
        category=evaluation_question.category,
        passed=passed,
        row_count=len(result.rows),
        attempts=result.attempts,
        duration_seconds=time.perf_counter() - started_at,
        reason=reason,
    )


def run_evaluation(
    settings: Settings,
    provider: Provider,
    *,
    max_rows: int = 20,
    questions: tuple[EvaluationQuestion, ...] = EVALUATION_QUESTIONS,
) -> list[EvaluationResult]:
    selected_questions = [
        question for question in questions if provider in question.providers
    ]
    return [
        evaluate_question(settings, question, provider, max_rows=max_rows)
        for question in selected_questions
    ]
