"""Deterministic question routing used as a no-model SQL baseline."""

from research_lens.analytics import METRICS


class UnsupportedQuestionError(ValueError):
    """Raised when the deterministic baseline cannot map a question to a metric."""


def generate_baseline_sql(question: str) -> str:
    normalized = " ".join(question.lower().split())

    if "open access" in normalized and any(
        word in normalized for word in ("year", "annual", "percentage", "percent")
    ):
        return METRICS["open-access-by-year"].sql

    institution_terms = ("institution", "university", "universities")
    if any(term in normalized for term in institution_terms) and any(
        word in normalized for word in ("publication", "paper", "work", "most", "top")
    ):
        return METRICS["institution-publications"].sql

    if "topic" in normalized and any(
        word in normalized for word in ("citation", "impact", "publication", "paper", "top")
    ):
        return METRICS["primary-topic-impact"].sql

    raise UnsupportedQuestionError(
        "The baseline supports institution publication rankings, yearly open-access "
        "rates, and primary-topic publication/citation impact."
    )
