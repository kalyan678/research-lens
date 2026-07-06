"""Streamlit interface for ResearchLens."""

from __future__ import annotations

import csv
from io import StringIO
from time import perf_counter

import duckdb
import streamlit as st

from research_lens.config import Settings
from research_lens.dashboard import (
    DatabaseNotInitializedError,
    load_entity_counts,
)
from research_lens.query_service import (
    Provider,
    QuestionRejectedError,
    QuestionResponse,
    answer_question,
)

EXAMPLE_QUESTIONS = (
    (
        "Institution leaders",
        "Which institutions have the most publications?",
    ),
    (
        "Open access by year",
        "What is the open access percentage by year?",
    ),
    (
        "Primary-topic impact",
        "Which primary topics have the highest citation impact?",
    ),
)


def _clear_results() -> None:
    st.session_state.pop("last_response", None)
    st.session_state.pop("last_duration_seconds", None)


def _set_question(question: str) -> None:
    _clear_results()
    st.session_state.question_input = question


def _table_data(response: QuestionResponse) -> dict[str, list[object]]:
    result = response.result
    return {
        column: [row[index] for row in result.rows]
        for index, column in enumerate(result.columns)
    }


def _results_csv(response: QuestionResponse) -> str:
    output = StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(response.result.columns)
    writer.writerows(response.result.rows)
    return output.getvalue()


def _render_sidebar(settings: Settings) -> tuple[Provider, int]:
    st.sidebar.title("ResearchLens")
    st.sidebar.caption("Private research analytics on your local machine")
    st.sidebar.divider()
    st.sidebar.header("Query settings")

    provider_labels: dict[str, Provider] = {
        "Deterministic baseline": "baseline",
        f"Ollama - {settings.ollama_model}": "ollama",
    }
    selected_label = st.sidebar.radio(
        "Query engine",
        options=list(provider_labels),
        captions=(
            "Fast, repeatable answers for the three tested metric families.",
            "Flexible schema-grounded SQL from your local model.",
        ),
        help=(
            "The baseline routes three supported question families to tested SQL. "
            "Ollama generates SQL from the full schema."
        ),
        key="provider_choice",
        on_change=_clear_results,
    )
    provider = provider_labels[selected_label]

    max_rows = st.sidebar.slider(
        "Maximum result rows",
        min_value=5,
        max_value=100,
        value=20,
        step=5,
        key="max_rows",
        on_change=_clear_results,
    )

    st.sidebar.divider()
    st.sidebar.subheader("Environment")
    st.sidebar.caption(f"Database\n`{settings.database_path}`")
    if provider == "baseline":
        st.sidebar.success("Baseline ready")
    elif settings.ollama_base_url:
        st.sidebar.success("Ollama ready")
    else:
        st.sidebar.warning("Ollama URL is not configured")

    with st.sidebar.expander("How queries stay safe"):
        st.markdown(
            """
            - One validated, read-only SQL statement
            - Known ResearchLens tables only
            - External file and network functions blocked
            - Result row cap enforced
            - At most one model correction attempt
            """
        )

    st.sidebar.caption("All database execution stays on this computer.")
    return provider, max_rows


def _render_entity_counts(counts: dict[str, int]) -> None:
    first_row = st.columns(3)
    first_row_labels = (
        ("works", "Works"),
        ("authors", "Authors"),
        ("institutions", "Institutions"),
    )
    for column, (key, label) in zip(first_row, first_row_labels, strict=True):
        column.metric(label, counts.get(key, 0))

    second_row = st.columns(2)
    second_row_labels = (
        ("topics", "Topics"),
        ("sources", "Sources"),
    )
    for column, (key, label) in zip(second_row, second_row_labels, strict=True):
        column.metric(label, counts.get(key, 0))


def _render_result(
    response: QuestionResponse,
    max_rows: int,
    duration_seconds: float | None,
) -> None:
    result = response.result
    with st.container(border=True):
        st.subheader("Analysis result")
        st.caption(f"Question: {result.question}")

        metadata_columns = st.columns(4)
        metadata_columns[0].caption("Provider")
        metadata_columns[0].markdown(f"**{response.provider_label}**")
        metadata_columns[1].metric("SQL attempts", result.attempts)
        metadata_columns[2].metric("Rows returned", len(result.rows))
        duration_label = (
            f"{duration_seconds:.2f}s" if duration_seconds is not None else "N/A"
        )
        metadata_columns[3].metric("Response time", duration_label)

        results_tab, sql_tab = st.tabs(["Results", "SQL and safety"])

        with results_tab:
            if result.rows:
                st.dataframe(
                    _table_data(response),
                    hide_index=True,
                    width="stretch",
                )
                result_actions = st.columns([1, 3])
                result_actions[0].download_button(
                    "Download CSV",
                    data=_results_csv(response),
                    file_name="research_lens_results.csv",
                    mime="text/csv",
                    key="download_results",
                    icon=":material/download:",
                    on_click="ignore",
                    width="stretch",
                )
                result_actions[1].caption(
                    f"Showing up to {max_rows} rows from a read-only query."
                )
            else:
                st.info("The query executed successfully but returned no rows.")

        with sql_tab:
            st.info(
                "This SQL passed the ResearchLens safety policy before DuckDB "
                "executed it through a read-only connection."
            )
            st.code(result.sql, language="sql")


def main() -> None:
    st.set_page_config(
        page_title="ResearchLens",
        page_icon="\U0001f50e",
        layout="centered",
    )

    settings = Settings.from_env()
    provider, max_rows = _render_sidebar(settings)

    with st.container(border=True):
        st.title("ResearchLens")
        st.subheader("Ask questions. Inspect SQL. Trust the result.")
        st.write(
            "Explore scholarly trends in plain language, review the generated "
            "SQL, and keep execution safely inside your local DuckDB database."
        )
        st.markdown("`LOCAL-FIRST`  `READ-ONLY SQL`  `OPENALEX DATA`")

    try:
        counts = load_entity_counts(settings.database_path)
    except (DatabaseNotInitializedError, duckdb.Error) as error:
        st.error(str(error))
        st.code("research-lens init-db", language="powershell")
        st.stop()

    st.subheader("Research snapshot")
    st.caption(
        "A quick view of the entities currently loaded in your local database."
    )
    with st.container(border=True):
        _render_entity_counts(counts)

    with st.expander("How to use ResearchLens"):
        st.markdown(
            """
            1. **Choose an engine.** Use the baseline for the tested examples or
               Ollama for broader schema-grounded questions.
            2. **Ask a question.** Start with an example or write your own.
            3. **Inspect the answer.** Review the result table, timing, and SQL.
            4. **Export if useful.** Download the returned rows as CSV.
            """
        )

    if "question_input" not in st.session_state:
        st.session_state.question_input = EXAMPLE_QUESTIONS[0][1]

    with st.container(border=True):
        st.subheader("Ask a research question")
        st.write(
            "Choose a tested example or write your own question. Use Ollama for "
            "questions outside the deterministic metric families."
        )

        example_columns = st.columns(len(EXAMPLE_QUESTIONS))
        for index, (label, question) in enumerate(EXAMPLE_QUESTIONS):
            example_columns[index].button(
                label,
                key=f"example_{index}",
                on_click=_set_question,
                args=(question,),
                width="stretch",
            )

        question = st.text_area(
            "Research question",
            key="question_input",
            height=100,
            placeholder="Example: Which institutions have the most publications?",
        )

        if provider == "baseline":
            st.info(
                "Baseline mode supports institution rankings, yearly open-access "
                "rates, and primary-topic impact."
            )
        elif not settings.ollama_base_url:
            st.warning("Configure OLLAMA_BASE_URL in .env before using Ollama.")

        question_is_empty = not question.strip()
        ollama_is_unavailable = (
            provider == "ollama" and not settings.ollama_base_url
        )
        action_columns = st.columns([3, 1])

        submitted = action_columns[0].button(
            "Run analysis",
            key="run_analysis",
            type="primary",
            icon=":material/search:",
            disabled=question_is_empty or ollama_is_unavailable,
            width="stretch",
        )

        action_columns[1].button(
            "Clear results",
            key="clear_results",
            on_click=_clear_results,
            width="stretch",
        )

    if submitted:
        started_at = perf_counter()
        status = st.status("Analysing your question...", expanded=True)
        try:
            status.write(f"Using {provider} query generation.")
            st.session_state.last_response = answer_question(
                settings,
                question,
                provider,
                max_rows=max_rows,
            )
            st.session_state.last_duration_seconds = perf_counter() - started_at
            status.write("SQL validated and executed through read-only DuckDB.")
            status.update(
                label="Analysis complete",
                state="complete",
                expanded=False,
            )
        except QuestionRejectedError as error:
            _clear_results()
            status.update(label="Analysis failed", state="error", expanded=True)
            st.error(f"Question rejected: {error}")

    response = st.session_state.get("last_response")
    if isinstance(response, QuestionResponse):
        duration_seconds = st.session_state.get("last_duration_seconds")
        _render_result(
            response,
            max_rows,
            duration_seconds if isinstance(duration_seconds, float) else None,
        )


main()
