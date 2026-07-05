from __future__ import annotations

import argparse
import sys

import httpx

from research_lens.agent import AgentResult, run_sql_agent
from research_lens.analytics import METRICS
from research_lens.baseline import UnsupportedQuestionError, generate_baseline_sql
from research_lens.config import Settings
from research_lens.database import (
    connect_database,
    database_is_reachable,
    initialize_schema,
)
from research_lens.normalization import normalize_work
from research_lens.openalex import OpenAlexClient
from research_lens.repository import ResearchRepository
from research_lens.schema import ALL_TABLES, CORE_TABLES
from research_lens.sql_safety import UnsafeQueryError, validate_read_only_query


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="research-lens")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("check", help="Check DuckDB and Ollama connectivity")
    subparsers.add_parser("init-db", help="Create the initial DuckDB schema")
    subparsers.add_parser("stats", help="Print row counts for core entities")
    subparsers.add_parser("metrics", help="List the named analytical metrics")

    describe = subparsers.add_parser("describe", help="Describe one ResearchLens table")
    describe.add_argument("table", choices=ALL_TABLES)

    metric = subparsers.add_parser("metric", help="Execute one named analytical metric")
    metric.add_argument("name", choices=METRICS)
    metric.add_argument("--max-rows", type=int, default=20)

    ask = subparsers.add_parser(
        "ask",
        help="Ask a supported natural-language question using the local baseline",
    )
    ask.add_argument("question")
    ask.add_argument("--max-rows", type=int, default=20)

    query = subparsers.add_parser("query", help="Execute one validated read-only SQL query")
    query.add_argument("--sql", required=True)
    query.add_argument("--max-rows", type=int, default=20)

    ingest = subparsers.add_parser("ingest", help="Ingest a bounded OpenAlex works slice")
    ingest.add_argument("--query", required=True)
    ingest.add_argument("--from-year", type=int, required=True)
    ingest.add_argument("--to-year", type=int, required=True)
    ingest.add_argument("--max-works", type=int, default=100)

    return parser


def _check(settings: Settings) -> int:
    connection = connect_database(settings.database_path)
    try:
        database_ok = database_is_reachable(connection)
    finally:
        connection.close()
    print(f"DuckDB: {'OK' if database_ok else 'FAILED'} ({settings.database_path})")

    if not settings.ollama_base_url:
        print("Ollama: SKIPPED (optional until the SQL-agent phase)")
        return 0 if database_ok else 1

    try:
        response = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=5.0)
        response.raise_for_status()
        installed_models = [model["name"] for model in response.json().get("models", [])]
        print(f"Ollama: OK ({', '.join(installed_models) or 'no models installed'})")
    except (httpx.HTTPError, KeyError, TypeError) as error:
        print(f"Ollama: UNAVAILABLE ({error})")
        print("Ollama is optional until the SQL-agent phase; data work can continue.")

    return 0 if database_ok else 1


def _stats(settings: Settings) -> None:
    connection = connect_database(settings.database_path)
    try:
        initialize_schema(connection)
        for table in CORE_TABLES:
            count = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"{table}: {count}")
    finally:
        connection.close()


def _print_rows(columns: list[str], rows: list[tuple[object, ...]]) -> None:
    def format_cell(value: object) -> str:
        rendered = "NULL" if value is None else str(value).replace("\n", " ")
        return rendered if len(rendered) <= 60 else f"{rendered[:57]}..."

    formatted_rows = [[format_cell(value) for value in row] for row in rows]
    widths = [
        min(
            60,
            max(
                len(column),
                *(len(row[index]) for row in formatted_rows),
            ),
        )
        for index, column in enumerate(columns)
    ]

    def render_row(values: list[str]) -> str:
        return " | ".join(value.ljust(widths[index]) for index, value in enumerate(values))

    print(render_row(columns))
    print("-+-".join("-" * width for width in widths))
    for row in formatted_rows:
        print(render_row(row))


def _describe(settings: Settings, table: str) -> None:
    connection = connect_database(settings.database_path, read_only=True)
    try:
        cursor = connection.execute(f"DESCRIBE {table}")
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]
        _print_rows(columns, rows)
    finally:
        connection.close()


def _list_metrics() -> None:
    for name, metric in METRICS.items():
        print(f"{name}: {metric.description}")


def _metric(settings: Settings, name: str, max_rows: int) -> int:
    metric = METRICS[name]
    print(f"{name}: {metric.description}\n")
    return _query(settings, metric.sql, max_rows)


def _print_agent_result(result: AgentResult, max_rows: int) -> None:
    print("Provider: deterministic baseline (not an LLM)")
    print(f"Question: {result.question}")
    print(f"SQL:\n{result.sql}\n")
    _print_rows(result.columns, result.rows)
    print(f"\nReturned {len(result.rows)} row(s), capped at {max_rows}.")


def _ask(settings: Settings, question: str, max_rows: int) -> int:
    try:
        result = run_sql_agent(
            question,
            lambda _prompt: generate_baseline_sql(question),
            settings.database_path,
            max_rows=max_rows,
        )
    except (UnsupportedQuestionError, UnsafeQueryError, ValueError) as error:
        print(f"Question rejected: {error}", file=sys.stderr)
        return 2

    _print_agent_result(result, max_rows)
    return 0


def _query(settings: Settings, sql: str, max_rows: int) -> int:
    if not 1 <= max_rows <= 1_000:
        print("--max-rows must be between 1 and 1000", file=sys.stderr)
        return 2

    try:
        validated_sql = validate_read_only_query(sql, ALL_TABLES)
    except UnsafeQueryError as error:
        print(f"Query rejected: {error}", file=sys.stderr)
        return 2

    connection = connect_database(settings.database_path, read_only=True)
    try:
        limited_sql = (
            f"SELECT * FROM ({validated_sql}) AS research_lens_result "
            f"LIMIT {max_rows}"
        )
        cursor = connection.execute(limited_sql)
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]
        _print_rows(columns, rows)
        print(f"\nReturned {len(rows)} row(s), capped at {max_rows}.")
    finally:
        connection.close()
    return 0


def _ingest(settings: Settings, args: argparse.Namespace) -> int:
    if not settings.openalex_api_key:
        print("OPENALEX_API_KEY is missing from .env", file=sys.stderr)
        return 2

    connection = connect_database(settings.database_path)
    initialize_schema(connection)
    repository = ResearchRepository(connection)
    ingested = 0

    connection.execute("BEGIN")
    try:
        with OpenAlexClient(settings.openalex_api_key) as client:
            for payload in client.iter_works(
                query=args.query,
                from_year=args.from_year,
                to_year=args.to_year,
                max_works=args.max_works,
            ):
                repository.upsert_work_bundle(normalize_work(payload))
                ingested += 1
                if ingested % 25 == 0:
                    print(f"Ingested {ingested} works...")
        connection.execute("COMMIT")
    except Exception:
        connection.execute("ROLLBACK")
        raise
    finally:
        connection.close()

    print(f"Ingestion complete: {ingested} works processed")
    return 0


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    settings = Settings.from_env()

    if args.command == "check":
        return _check(settings)
    if args.command == "init-db":
        connection = connect_database(settings.database_path)
        try:
            initialize_schema(connection)
        finally:
            connection.close()
        print(f"Database schema initialized at {settings.database_path}")
        return 0
    if args.command == "stats":
        _stats(settings)
        return 0
    if args.command == "metrics":
        _list_metrics()
        return 0
    if args.command == "describe":
        _describe(settings, args.table)
        return 0
    if args.command == "metric":
        return _metric(settings, args.name, args.max_rows)
    if args.command == "ask":
        return _ask(settings, args.question, args.max_rows)
    if args.command == "query":
        return _query(settings, args.sql, args.max_rows)
    if args.command == "ingest":
        return _ingest(settings, args)

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
