# ResearchLens Portfolio Summary

## One-line description

ResearchLens is a local-first research intelligence assistant that turns plain
English questions about scholarly metadata into safe, inspectable SQL over a
DuckDB analytical database.

## Problem

Research teams often need quick answers from publication metadata, but the data
is relational and requires SQL knowledge. A naive natural-language SQL agent can
be risky because generated SQL may be wrong, slow, or unsafe. ResearchLens
addresses this by combining deterministic query templates, a local model
fallback, SQL validation, and read-only execution.

## Solution

The project ingests real OpenAlex metadata, normalizes it into a local DuckDB
schema, and supports analysis through both a CLI and a Streamlit interface.
Users can ask questions such as:

- Which institutions have the most publications?
- What is the open access percentage by year?
- Which primary topics have the highest citation impact?
- Which authors and institutions are linked to a named paper?

The recommended hybrid query engine routes known analytical intents to tested
deterministic SQL templates and keeps Ollama available for exploratory fallback
questions.

## Key engineering decisions

- Used DuckDB instead of PostgreSQL to keep the project local, portable, and
  beginner-friendly without Docker.
- Added explicit SQL safety checks instead of relying only on prompt
  instructions.
- Used read-only database connections for generated SQL execution.
- Added one bounded correction attempt when DuckDB rejects otherwise safe model
  SQL.
- Added a hybrid provider after pure Ollama evaluation showed high latency and
  inconsistent accuracy.
- Built a repeatable evaluation command instead of relying only on manual demo
  prompts.

## Current dataset

The local demo has been tested with a bounded OpenAlex slice for `large
language models` from 2023 through 2026:

| Entity | Count |
|---|---:|
| Works | 300 |
| Authors | 1,984 |
| Institutions | 557 |
| Topics | 146 |
| Sources | 119 |

## Evaluation result

On the 300-work local dataset:

| Provider | Result | Interpretation |
|---|---:|---|
| Baseline | 7/7 | Fast deterministic templates for covered questions. |
| Hybrid | 7/7 | Recommended mode; combines reliability with model fallback. |
| Ollama `qwen2.5-coder:3b` | 4/7 | Useful but slower and less reliable for full-suite automation. |

This is intentionally not presented as production accuracy. The evaluation is a
portfolio-scale proof that the system is testable, measurable, and designed
with safety boundaries.

## Tech stack

- Python
- DuckDB
- OpenAlex API
- Ollama with `qwen2.5-coder:3b`
- SQLGlot
- Streamlit
- pytest
- Ruff

## What this project demonstrates

- Building a complete local data application from ingestion to UI.
- Designing relational schemas for analytical questions.
- Writing SQL joins and aggregate metrics over normalized data.
- Integrating a local LLM without giving it unrestricted execution access.
- Creating safer NL-to-SQL workflows with validation and read-only execution.
- Using evaluation results to improve architecture instead of only changing
  prompts.

## Next improvements

- Add CI so tests run automatically on GitHub.
- Add a small cached sample dataset or reproducible fixture for demo setup.
- Add more evaluation questions across author, source, country, and year-trend
  use cases.
- Package the Streamlit app for easier local launch.
