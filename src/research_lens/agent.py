"""Natural-language SQL agent pipeline."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import duckdb

from research_lens.database import connect_database
from research_lens.schema import ALL_TABLES
from research_lens.sql_safety import validate_read_only_query


@dataclass(frozen=True)
class AgentResult:
    question: str
    sql: str
    columns: list[str]
    rows: list[tuple[object, ...]]
    attempts: int


class AgentQueryExecutionError(RuntimeError):
    """Raised when model-generated SQL still fails after one correction attempt."""


SCHEMA_CONTEXT = """
works(
    id, doi, title, publication_year, publication_date, work_type, language,
    cited_by_count, is_open_access, open_access_status, source_id,
    openalex_updated_date
)
authors(id, display_name, orcid)
institutions(id, display_name, country_code, institution_type)
topics(id, display_name, domain_name, field_name, subfield_name)
sources(id, display_name, source_type, issn_l, host_organization)
work_authors(work_id, author_id, author_position, is_corresponding)
work_author_institutions(work_id, author_id, institution_id)
work_topics(work_id, topic_id, score, is_primary)

Relationships:
- works.id = work_authors.work_id
- authors.id = work_authors.author_id
- works.id = work_author_institutions.work_id
- authors.id = work_author_institutions.author_id
- institutions.id = work_author_institutions.institution_id
- works.id = work_topics.work_id
- topics.id = work_topics.topic_id
- sources.id = works.source_id
""".strip()


def extract_sql(model_response: str) -> str:
    cleaned = model_response.strip()

    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        sql_lines = lines[1:]
        if sql_lines and sql_lines[-1].strip() == "```":
            sql_lines = sql_lines[:-1]
        cleaned = "\n".join(sql_lines)

    return cleaned.strip()


def _build_sql_instructions(question: str) -> str:
    cleaned_question = question.strip()
    if not cleaned_question:
        raise ValueError("Question cannot be empty")

    return f"""
You generate DuckDB SQL for the ResearchLens scholarly analytics database.

Rules:
1. Return exactly one read-only SELECT query. A WITH clause is allowed.
2. Use only the tables and columns in the schema below.
3. Return SQL only, without Markdown fences, comments, or explanation.
4. Never use DDL, DML, PRAGMA, ATTACH, COPY, or external file/network functions.
5. When counting publications after joining an authorship or affiliation table,
   use COUNT(DISTINCT work_id) to avoid counting one work once per author.
6. Do not invent missing data or columns.
7. Round percentages and averages to two decimal places.
8. Add deterministic ORDER BY clauses to grouped or ranked results, including
   a readable secondary sort for ties.
9. Do not use LIMIT 1 for plural ranking questions unless the user requests
   only the single top result.
10. When grouping a named entity, group by both its stable id and display name.
11. For institution or affiliation questions, use work_author_institutions.
    The work_authors table does not contain institution_id.
12. Prefer simple SQL over unnecessary CTEs.
13. Use stable readable aliases when relevant:
    institution, publication_count, total_publications,
    open_access_publications, open_access_percentage, topic,
    average_citations, author.

Schema:
{SCHEMA_CONTEXT}

Question:
{cleaned_question}
""".strip()


def build_sql_prompt(question: str) -> str:
    return f"{_build_sql_instructions(question)}\n\nSQL:"


def build_sql_correction_prompt(
    question: str,
    failed_sql: str,
    database_error: str,
) -> str:
    return f"""
{_build_sql_instructions(question)}

The previous SQL attempt failed during DuckDB execution.

Failed SQL:
{failed_sql}

DuckDB error:
{database_error}

Start the query again instead of repeating the failed joins.
Verify that every referenced column belongs to its table alias.
For an author-to-institution relationship, join through
work_author_institutions(work_id, author_id, institution_id).
Correct the table and column relationships using the supplied schema.
Return only one corrected read-only SELECT query.

Corrected SQL:
""".strip()


def _execute_read_only_query(
    database_path: Path,
    sql: str,
    max_rows: int,
) -> tuple[list[str], list[tuple[object, ...]]]:
    connection = connect_database(database_path, read_only=True)
    try:
        limited_sql = (
            f"SELECT * FROM ({sql}) AS research_lens_agent_result "
            f"LIMIT {max_rows}"
        )
        cursor = connection.execute(limited_sql)
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]
        return columns, rows
    finally:
        connection.close()


def run_sql_agent(
    question: str,
    generate: Callable[[str], str],
    database_path: Path,
    *,
    max_rows: int = 20,
) -> AgentResult:
    if not 1 <= max_rows <= 1_000:
        raise ValueError("max_rows must be between 1 and 1000")

    cleaned_question = question.strip()
    prompt = build_sql_prompt(cleaned_question)

    for attempt in range(2):
        model_response = generate(prompt)
        sql = extract_sql(model_response)
        validated_sql = validate_read_only_query(sql, ALL_TABLES)

        try:
            columns, rows = _execute_read_only_query(
                database_path,
                validated_sql,
                max_rows,
            )
        except duckdb.Error as error:
            if attempt == 1:
                raise AgentQueryExecutionError(
                    f"Model SQL failed after one correction attempt: {error}"
                ) from error
            prompt = build_sql_correction_prompt(
                cleaned_question,
                validated_sql,
                str(error),
            )
            continue

        return AgentResult(
            question=cleaned_question,
            sql=validated_sql,
            columns=columns,
            rows=rows,
            attempts=attempt + 1,
        )

    raise AssertionError("SQL agent loop ended unexpectedly")
