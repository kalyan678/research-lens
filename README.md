# ResearchLens

ResearchLens is a local-first research intelligence assistant. It loads real
scholarly metadata from OpenAlex into DuckDB and lets users ask analytical
questions in natural language through a guarded SQL agent backed by Ollama.

The project is intentionally being built in vertical slices. Every phase must
produce something runnable and testable before the next phase begins.

## Product question

How can a university, R&D team, founder, or research strategist explore
publication trends, institutional strengths, collaboration networks, open
access, and citation growth without hand-writing complex SQL?

## Architecture

```text
OpenAlex API
    |
    v
Ingestion + normalization
    |
    v
DuckDB analytical model
    |
    v
Safe SQL agent (Ollama)
    |
    v
API/UI: answer + SQL + data + visualization
```

## Delivery roadmap

1. **Foundation:** configuration, DuckDB, health checks, package structure.
2. **Data pipeline:** retrieve, normalize, upsert, and incrementally refresh OpenAlex data.
3. **Analytics model:** documented metrics and curated analytical views.
4. **Safe SQL agent:** schema selection, SQL generation, validation, execution, and explanation.
5. **Product interface:** API plus a usable analytical chat interface.
6. **Evaluation:** gold questions, execution accuracy, safety tests, and latency tracking.
7. **Production hardening:** migrations, observability, caching, CI, and deployment documentation.

## Milestone 1

The first executable milestone is:

```text
OpenAlex search -> normalize records -> DuckDB -> verify row counts
```

It deliberately excludes the LLM. If the data layer is unreliable, adding an
agent only makes the unreliability more theatrical.

## Local setup

Prerequisites:

- Python 3.11 or newer
- VS Code with the Microsoft Python extension
- A free OpenAlex API key

Ollama is deliberately optional until the SQL-agent phase. The data pipeline,
schema, analytical SQL, and tests do not depend on an LLM.

### Day 1: verify Python

Open a regular PowerShell window and run:

```powershell
py --version
```

If that command fails, install Python from python.org and enable the installer's
**Add Python to PATH** option. Close and reopen PowerShell afterward.

### Day 1: create the local environment

Open this project folder in VS Code, then open **Terminal > New Terminal**.
Run:

```powershell
Copy-Item .env.example .env
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

Select `.venv\Scripts\python.exe` if VS Code asks which Python interpreter to
use.

Edit `.env`:

```dotenv
DATABASE_PATH=data/research_lens.duckdb
OPENALEX_API_KEY=replace_with_your_key
OLLAMA_BASE_URL=
OLLAMA_MODEL=qwen3:8b
```

Do not commit or share `.env`.

### Day 1: verify the foundation

```powershell
research-lens check
research-lens init-db
pytest
```

`init-db` creates `data/research_lens.duckdb`. DuckDB requires no service,
database account, port, or Docker container.

`check` reports Ollama as skipped when `OLLAMA_BASE_URL` is blank. This is
expected during the data-engineering milestones.

### Day 2: ingest the first real dataset slice

Ingest a small, inspectable slice:

```powershell
research-lens ingest `
  --query "large language models" `
  --from-year 2024 `
  --to-year 2025 `
  --max-works 100
```

Check the resulting counts:

```powershell
research-lens stats
```

## Explore the analytical model

Inspect a table before querying it:

```powershell
research-lens describe works
research-lens describe work_author_institutions
```

Run one validated, read-only query:

```powershell
research-lens query --sql "SELECT publication_year, COUNT(*) AS publications FROM works GROUP BY publication_year ORDER BY publication_year"
```

List and execute the documented business metrics:

```powershell
research-lens metrics
research-lens metric institution-publications --max-rows 10
research-lens metric open-access-by-year
research-lens metric primary-topic-impact --max-rows 10
```

The query command accepts exactly one `SELECT` statement, restricts access to
ResearchLens tables, blocks external file/network functions, opens DuckDB in
read-only mode, and caps displayed results.

## Engineering principles

- The agent opens the DuckDB file in read-only mode.
- Generated SQL is parsed and validated before execution.
- Destructive statements are rejected in code, not merely discouraged in a prompt.
- Every business metric has a written definition.
- Agent quality is measured with reproducible questions and expected results.
- Raw API payloads are never treated as a ready-made analytical schema.
- Relationships are represented by stable OpenAlex IDs and validated by tests.
  DuckDB foreign-key constraints are intentionally omitted because its current
  update implementation cannot update referenced parent rows safely.
