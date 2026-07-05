# ResearchLens

ResearchLens is a local-first research intelligence assistant. It loads real
scholarly metadata from OpenAlex into DuckDB and lets users ask analytical
questions in natural language through a guarded SQL agent backed by Ollama.

**MVP status:** complete as a tested command-line application. The current
version includes real data ingestion, reusable metrics, a deterministic
baseline, local model-backed SQL generation, bounded reflection, and read-only
query enforcement.

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
    ^
    |
Natural-language question
    |
    +---- deterministic metric baseline
    |
    +---- Ollama -> SQL extraction -> validation
                                  |
                                  v
                         read-only execution
                                  |
                    one correction on DuckDB error
```

## Delivered MVP

- OpenAlex ingestion and relational normalization
- Local DuckDB analytical model
- Three documented business metrics
- Validated read-only SQL execution
- Deterministic natural-language baseline
- Local Ollama provider with bounded generation
- One-attempt SQL reflection using DuckDB error feedback
- Automated behavioural and safety tests

Optional future work includes a web interface, larger evaluation dataset,
incremental ingestion audit records, caching, CI, and deployment packaging.

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
- Ollama for optional local model-backed questions

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
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder:3b
OLLAMA_TIMEOUT_SECONDS=300
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

Ask one of those question families through the deterministic local baseline:

```powershell
research-lens ask "Which institutions have the most publications?" --max-rows 10
research-lens ask "What is the open access percentage by year?"
research-lens ask "Which primary topics have the highest citation impact?" --max-rows 10
```

The baseline is deliberately labelled as not being an LLM. It routes supported
question patterns to tested metric SQL, providing a reliable benchmark and a
fully local fallback while the replaceable model integration is developed.

After installing Ollama locally and setting `OLLAMA_BASE_URL` and
`OLLAMA_MODEL` in `.env`, ask unrestricted schema-grounded questions through
the model. `OLLAMA_TIMEOUT_SECONDS` defaults to 300 for CPU-only laptops:

```powershell
research-lens check
research-lens ask "How many publications are there by year?" --provider ollama
```

The model only proposes SQL. ResearchLens strips optional Markdown fences,
parses and validates the SQL, rejects non-read-only operations, executes it
through a read-only DuckDB connection, and caps the returned rows. If DuckDB
rejects a safe query because of an invalid table-column relationship, the agent
gives the error to the model and allows exactly one correction attempt.

The query command accepts exactly one `SELECT` statement, restricts access to
ResearchLens tables, blocks external file/network functions, opens DuckDB in
read-only mode, and caps displayed results.

## Evaluation

The MVP was evaluated on five representative analytical questions using
`qwen2.5-coder:3b` locally. Initial evaluation exposed ambiguous ranking
behaviour, missing numeric rounding, and an invalid author-institution join.
Prompt refinement and a bounded correction loop produced correct executable
results for all five scenarios. The initial failures and final outcomes are
recorded in [docs/evaluation.md](docs/evaluation.md).

Run the complete deterministic verification:

```powershell
pytest -q
ruff check src tests
```

## Limitations

- The demonstration database contains only 25 search-selected works and is not
  representative of the global research landscape.
- Citation counts measure attention, not research quality, and are affected by
  publication age and outliers.
- Small local models can generate valid but unnecessarily complex SQL.
- Model-backed answers are nondeterministic; the deterministic baseline remains
  the trusted comparison for the three core metrics.
- The MVP is a CLI application. A web UI and production deployment are outside
  the current scope.

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
