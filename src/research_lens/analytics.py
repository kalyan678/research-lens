"""Named, reusable business metrics for the ResearchLens analytical model."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Metric:
    description: str
    sql: str


METRICS = {
    "institution-publications": Metric(
        description=(
            "Unique publications associated with each institution through "
            "author affiliations."
        ),
        sql="""
            SELECT
                i.display_name AS institution,
                COUNT(DISTINCT wai.work_id) AS publication_count
            FROM work_author_institutions AS wai
            JOIN institutions AS i
                ON i.id = wai.institution_id
            GROUP BY i.id, i.display_name
            ORDER BY publication_count DESC, institution
        """,
    ),
    "open-access-by-year": Metric(
        description="Publication and open-access counts and percentage by year.",
        sql="""
            SELECT
                publication_year,
                COUNT(*) AS total_publications,
                SUM(
                    CASE WHEN is_open_access THEN 1 ELSE 0 END
                ) AS open_access_publications,
                ROUND(
                    100.0
                    * SUM(CASE WHEN is_open_access THEN 1 ELSE 0 END)
                    / COUNT(*),
                    2
                ) AS open_access_percentage
            FROM works
            GROUP BY publication_year
            ORDER BY publication_year
        """,
    ),
    "primary-topic-impact": Metric(
        description=(
            "Publication count and average citations for each primary research topic."
        ),
        sql="""
            SELECT
                t.display_name AS topic,
                COUNT(DISTINCT wt.work_id) AS publication_count,
                ROUND(AVG(w.cited_by_count), 2) AS average_citations
            FROM work_topics AS wt
            JOIN topics AS t
                ON t.id = wt.topic_id
            JOIN works AS w
                ON w.id = wt.work_id
            WHERE wt.is_primary = TRUE
            GROUP BY t.id, t.display_name
            ORDER BY publication_count DESC, average_citations DESC
        """,
    ),
}
