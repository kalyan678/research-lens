# ResearchLens

ResearchLens is a local-first research intelligence assistant that converts
natural-language questions into safe, read-only SQL. It ingests scholarly
metadata from OpenAlex, stores it in DuckDB, and uses either deterministic
metrics or a local Ollama model to analyse publication trends, institutional
activity, open-access rates, and topic impact.

**Current status:** tested CLI and local Streamlit application.

## Why ResearchLens?

Research teams often need answers from scholarly metadata but may not know the
database schema or the SQL required to query it. ResearchLens provides a
reproducible local workflow for loading real publication data and exploring it
in plain language while keeping query execution constrained and inspectable.

## Key capabilities

- Ingest a bounded, searchable slice of real OpenAlex metadata.
- Normalize works, authors, institutions, topics, sources, and relationships.
- Store the analytical model locally in DuckDB without a database server or
  Docker.
- Run three documented metrics for institutional activity, open access, and
  primary-topic impact.
- Translate supported questions through a deterministic baseline or a local
  Ollama model.
- Explore entity counts, example questions, generated SQL, and tabular results
  through a local Streamlit interface.
- Display the generated SQL alongside the result.
- Parse and validate SQL before opening a read-only database connection.
- Allow one bounded model correction when DuckDB rejects an otherwise safe
  query.
- Verify analytical behaviour and safety controls with automated tests.

## Architecture

```text
OpenAlex API
     |
     v
Ingestion and normalization
     |
     v
DuckDB analytical model

CLI or Streamlit question
     |
     +-- Deterministic metric baseline --+
     |                                   |
     +-- Ollama SQL generation ----------+--> SQL validation
                                                 |
                                                 v
                                      Read-only DuckDB execution
                                                 |
                                      One bounded correction
                                      on an execution error
```

## Technology stack

| Component | Purpose |
|---|---|
| Python | Application and CLI |
| OpenAlex | Scholarly metadata source |
| DuckDB | Embedded analytical database |
| Ollama | Optional local language-model runtime |
| SQLGlot | SQL parsing and safety validation |
| Streamlit | Local interactive web interface |
| pytest and Ruff | Automated testing and code quality |

## Quick start

### Prerequisites

- Python 3.11 or newer
- A free OpenAlex API key
- Ollama and a local model only if you want model-generated SQL

The ingestion pipeline, analytical metrics, deterministic baseline, and tests
work without Ollama.

### Install

The following commands use PowerShell:

```powershell
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

Configure `.env`:

```dotenv
DATABASE_PATH=data/research_lens.duckdb
OPENALEX_API_KEY=replace_with_your_key
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder:3b
OLLAMA_TIMEOUT_SECONDS=300
```

Do not commit or share `.env`. Leave `OLLAMA_BASE_URL` blank if you are not
using Ollama.

Initialize and verify the application:

```powershell
research-lens init-db
research-lens check
pytest -q
```

DuckDB runs as a local file and requires no service, account, port, or
container.

## Load research data

This example loads up to 100 works matching a topic and publication period:

```powershell
research-lens ingest `
  --query "large language models" `
  --from-year 2024 `
  --to-year 2025 `
  --max-works 100

research-lens stats
```

## Launch the web interface

Start the local Streamlit application after initializing and loading the
database:

```powershell
python -m streamlit run streamlit_app.py --server.address 127.0.0.1
```

The application opens in your browser and uses the same query service and
safety pipeline as the CLI. Binding to `127.0.0.1` keeps the development server
accessible only from the local machine.

## Explore the data

Inspect the schema:

```powershell
research-lens describe works
research-lens describe work_author_institutions
```

List and run the documented metrics:

```powershell
research-lens metrics
research-lens metric institution-publications --max-rows 10
research-lens metric open-access-by-year
research-lens metric primary-topic-impact --max-rows 10
```

Ask a supported question through the deterministic baseline:

```powershell
research-lens ask "Which institutions have the most publications?" --max-rows 10
research-lens ask "What is the open access percentage by year?"
research-lens ask "Which primary topics have the highest citation impact?" --max-rows 10
```

Ask a broader, schema-grounded question through Ollama:

```powershell
research-lens ask "How many publications are there by year?" --provider ollama
```

You can also execute one validated read-only query directly:

```powershell
research-lens query --sql "SELECT publication_year, COUNT(*) AS publications FROM works GROUP BY publication_year ORDER BY publication_year"
```

## Safety design

The model proposes SQL but never receives unrestricted database access.
ResearchLens:

- accepts exactly one `SELECT` statement, including queries beginning with
  `WITH`;
- restricts queries to known ResearchLens tables;
- blocks destructive statements and external file or network functions;
- executes through a read-only DuckDB connection;
- caps the number of displayed rows; and
- sends an execution error back to the model at most once for correction.

These restrictions are enforced in application code rather than relying only
on prompt instructions.

## Evaluation

The CLI MVP was evaluated with five representative analytical questions using
`qwen2.5-coder:3b`. All five scenarios ultimately produced correct executable
results after prompt refinement, but the initial run included one failure, one
partial result, and two presentation-quality issues.

See [the evaluation report](docs/evaluation.md) for the acceptance criteria,
initial outcomes, corrected outcomes, and known model limitations.

Run the complete deterministic verification:

```powershell
pytest -q
ruff check src tests
```

## Current limitations

- The demonstration database contains only 25 search-selected works and cannot
  represent the global research landscape.
- Citation counts indicate attention, not research quality, and are affected by
  publication age and outliers.
- The five-question evaluation set is too small for a production-quality
  accuracy claim.
- Small local models can produce valid but unnecessarily complex SQL, and their
  outputs are nondeterministic.
- The Streamlit interface is designed for local use and is not yet packaged for
  public deployment.

## Roadmap

- Expand the demonstration dataset and evaluation suite.
- Add continuous integration and release-quality documentation.
- Explore caching, incremental-ingestion audit records, and deployment
  packaging.
