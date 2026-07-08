# ResearchLens

[![CI](https://github.com/kalyan678/research-lens/actions/workflows/ci.yml/badge.svg)](https://github.com/kalyan678/research-lens/actions/workflows/ci.yml)

ResearchLens is a local-first research intelligence assistant that converts
natural-language questions into safe, read-only SQL. It ingests scholarly
metadata from OpenAlex, stores it in DuckDB, and uses either deterministic
SQL templates, a hybrid router, or a local Ollama model to analyse publication
trends, institutional activity, open-access rates, topic impact, and named-paper
author affiliations.

**Current status:** tested CLI, local Streamlit application, expanded
300-work dataset, hybrid query routing, and repeatable evaluation harness.

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
- Run documented analytical templates for institutional activity, open access,
  primary-topic impact, and named-paper author affiliations.
- Translate questions through a recommended hybrid router, deterministic
  baseline, or local Ollama model.
- Explore entity counts, example questions, generated SQL, and tabular results
  through a local Streamlit interface.
- Evaluate baseline, hybrid, and Ollama question answering with a repeatable
  CLI evaluation suite.
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
     +-- Hybrid router ------------------+
     |       |
     |       +-- Deterministic templates -+
     |       |
     |       +-- Ollama fallback ---------+--> SQL validation
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
work without Ollama. Hybrid mode also works without Ollama for covered
deterministic question families.

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

For a richer portfolio-sized local demo, this project has also been tested
with 300 OpenAlex works for `large language models` from 2023 through 2026.

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

Ask a question through the recommended hybrid provider:

```powershell
research-lens ask "Which institutions have the most publications?" --max-rows 10
research-lens ask "What is the open access percentage by year?"
research-lens ask "List each author and institution for the paper titled 'Bias and Fairness in Large Language Models: A Survey'."
```

Ask the same supported question families through the deterministic baseline:

```powershell
research-lens ask "Which primary topics have the highest citation impact?" --provider baseline --max-rows 10
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

ResearchLens includes a repeatable natural-language evaluation command. It
checks whether generated answers execute safely, return enough rows, and expose
the expected analytical columns.

Run the recommended hybrid evaluation:

```powershell
research-lens eval --provider hybrid --max-rows 20
```

On the 300-work local dataset, hybrid mode passed all seven evaluation
questions. The covered deterministic paths finished in under one second per
question during the latest run.

Run the deterministic baseline evaluation:

```powershell
research-lens eval --provider baseline --max-rows 20
```

The deterministic baseline also passed all seven supported evaluation
questions after adding a named-paper author-affiliation template.

Run the local model evaluation:

```powershell
research-lens eval --provider ollama --max-rows 20
```

With `qwen2.5-coder:3b`, the first automated Ollama evaluation passed four of
seven questions. The failures were useful engineering signals: local model
latency was high, and some valid-looking answers used column aliases that did
not match the stricter evaluator expectations.

See [the evaluation report](docs/evaluation.md) for the acceptance criteria,
outcomes, and known model limitations.

For a concise project narrative, see
[the portfolio summary](docs/portfolio-summary.md).

Run the complete deterministic verification:

```powershell
pytest -q
ruff check src tests
```

## Current limitations

- The demonstration database contains a bounded 300-work OpenAlex slice and
  cannot represent the global research landscape.
- Citation counts indicate attention, not research quality, and are affected by
  publication age and outliers.
- The seven-question evaluation set is still too small for a
  production-quality accuracy claim.
- Small local models can produce invalid or unnecessarily complex SQL, and
  their outputs are nondeterministic and sometimes slow. Hybrid mode reduces
  this risk by routing known intents to deterministic templates.
- The Streamlit interface is designed for local use and is not yet packaged for
  public deployment.

## Roadmap

- Add continuous integration.
- Add release-quality setup and troubleshooting documentation.
- Explore caching, incremental-ingestion audit records, and deployment
  packaging.
