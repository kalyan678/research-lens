from __future__ import annotations

from collections.abc import Collection

from sqlglot import exp, parse


class UnsafeQueryError(ValueError):
    """Raised when SQL does not satisfy the read-only query policy."""


FORBIDDEN_EXPRESSION_NAMES = {
    "Alter",
    "Attach",
    "Command",
    "Copy",
    "Create",
    "Delete",
    "Detach",
    "Drop",
    "Insert",
    "Install",
    "Load",
    "Merge",
    "Pragma",
    "Transaction",
    "TruncateTable",
    "Update",
    "Use",
}

EXTERNAL_ACCESS_FUNCTIONS = {
    "glob",
    "httpfs",
    "parquet_scan",
    "postgres_scan",
    "read_csv",
    "read_csv_auto",
    "read_json",
    "read_json_auto",
    "read_ndjson",
    "read_parquet",
    "sqlite_scan",
}


def validate_read_only_query(sql: str, allowed_tables: Collection[str]) -> str:
    if not sql.strip():
        raise UnsafeQueryError("SQL query cannot be empty")

    try:
        statements = parse(sql, read="duckdb")
    except Exception as error:
        raise UnsafeQueryError(f"SQL could not be parsed: {error}") from error

    if len(statements) != 1:
        raise UnsafeQueryError("Exactly one SQL statement is allowed")

    statement = statements[0]
    if not isinstance(statement, exp.Query):
        raise UnsafeQueryError("Only SELECT queries are allowed")

    for node in statement.walk():
        if node.__class__.__name__ in FORBIDDEN_EXPRESSION_NAMES:
            raise UnsafeQueryError(f"Forbidden SQL operation: {node.__class__.__name__}")

        if isinstance(node, exp.Func):
            function_name = (
                node.name if isinstance(node, exp.Anonymous) else node.sql_name()
            ).lower()
            if function_name in EXTERNAL_ACCESS_FUNCTIONS:
                raise UnsafeQueryError(
                    f"External file or network function is not allowed: {function_name}"
                )

    cte_names = {
        cte.alias_or_name.lower()
        for cte in statement.find_all(exp.CTE)
        if cte.alias_or_name
    }
    referenced_tables = {
        table.name.lower()
        for table in statement.find_all(exp.Table)
        if table.name and table.name.lower() not in cte_names
    }
    allowed = {table.lower() for table in allowed_tables}
    unknown_tables = sorted(referenced_tables - allowed)
    if unknown_tables:
        raise UnsafeQueryError(
            f"Query references tables outside ResearchLens: {', '.join(unknown_tables)}"
        )

    return statement.sql(dialect="duckdb")

