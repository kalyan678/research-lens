"""Deterministic question routing used as a no-model SQL baseline."""

import re

from research_lens.analytics import METRICS


class UnsupportedQuestionError(ValueError):
    """Raised when the deterministic baseline cannot map a question to a metric."""


def _sql_string_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _extract_quoted_title(question: str) -> str | None:
    match = re.search(
        r"\btitled\s+(?:'([^']+)'|\"([^\"]+)\")",
        question,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    title = match.group(1) or match.group(2)
    return title.strip()


def generate_baseline_sql(question: str) -> str:
    normalized = " ".join(question.lower().split())

    if "open access" in normalized and any(
        word in normalized for word in ("year", "annual", "percentage", "percent")
    ):
        return METRICS["open-access-by-year"].sql

    if "author" in normalized and any(
        term in normalized for term in ("institution", "affiliation")
    ):
        title = _extract_quoted_title(question)
        if not title:
            raise UnsupportedQuestionError(
                "Author-affiliation detail questions require a quoted title, "
                "for example: paper titled 'Example Title'."
            )
        title_literal = _sql_string_literal(title)
        return (
            "SELECT a.display_name AS author, i.display_name AS institution "
            "FROM works AS w "
            "JOIN work_author_institutions AS wai ON wai.work_id = w.id "
            "JOIN authors AS a ON a.id = wai.author_id "
            "JOIN institutions AS i ON i.id = wai.institution_id "
            f"WHERE w.title = {title_literal} "
            "ORDER BY institution, author"
        )


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
