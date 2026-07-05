import pytest

from research_lens.analytics import METRICS
from research_lens.baseline import UnsupportedQuestionError, generate_baseline_sql


@pytest.mark.parametrize(
    ("question", "metric_name"),
    [
        (
            "Which institutions have the most publications?",
            "institution-publications",
        ),
        (
            "What is the open access percentage by year?",
            "open-access-by-year",
        ),
        (
            "Which primary topics have the highest citation impact?",
            "primary-topic-impact",
        ),
        (
            "Which universities published the most papers?",
            "institution-publications",
        ),
    ],
)
def test_generate_baseline_sql_routes_supported_questions(
    question: str,
    metric_name: str,
) -> None:
    assert generate_baseline_sql(question) == METRICS[metric_name].sql


def test_generate_baseline_sql_normalizes_case_and_whitespace() -> None:
    assert generate_baseline_sql(
        "  TOP INSTITUTIONS   BY PUBLICATION  "
    ) == METRICS["institution-publications"].sql


def test_generate_baseline_sql_rejects_unknown_question() -> None:
    with pytest.raises(UnsupportedQuestionError, match="baseline supports"):
        generate_baseline_sql("Who wrote the earliest paper?")
