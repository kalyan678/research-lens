# ResearchLens Evaluation

Evaluation dates: 2026-07-05 and 2026-07-07

## Environment

- Model: `qwen2.5-coder:3b`
- Runtime: Ollama on Windows
- Model allocation observed by `ollama ps`: 2.5 GB
- Processing observed: 75% CPU / 25% GPU
- Context allocation: 4096 tokens
- Database: DuckDB with a bounded OpenAlex search slice
  - MVP run: 25 works
  - Expanded Day 2 run: 300 works for `large language models`, 2023-2026

## Acceptance criteria

A question passes when the generated SQL:

1. is accepted by the read-only safety policy;
2. executes against DuckDB;
3. uses the correct tables, relationships, and aggregation;
4. returns the expected business result; and
5. does not modify data.

Formatting and unnecessary SQL complexity are recorded separately from
business-result correctness.

## Automated evaluation command

ResearchLens now includes a repeatable evaluation harness:

```powershell
research-lens eval --provider baseline --max-rows 20
research-lens eval --provider ollama --max-rows 20
```

The evaluator checks row counts and expected analytical column groups. This is
not a full semantic proof, but it is stronger than manual smoke testing because
the same question set can be run after prompt, schema, model, or data changes.

## Day 2 expanded-data results

Dataset after expansion:

| Entity | Count |
|---|---:|
| Works | 300 |
| Authors | 1,984 |
| Institutions | 557 |
| Topics | 146 |
| Sources | 119 |

Deterministic baseline result:

| Provider | Questions | Passed | Notes |
|---|---:|---:|---|
| Baseline | 6 | 6 | Fast deterministic routing to documented metrics. |

First automated Ollama result:

| Provider | Questions | Passed | Notes |
|---|---:|---:|---|
| Ollama `qwen2.5-coder:3b` | 7 | 4 | Correct execution on several scenarios, but high latency and alias variation caused failures in the stricter evaluator. |

Observed Ollama latency ranged from about 100 to 171 seconds per question on
the local machine during the first full evaluation run. The CLI now prints
per-question progress so longer model evaluations do not look frozen.

## MVP manual evaluation results

| Scenario | Initial outcome | Final outcome | Observation |
|---|---|---|---|
| Publications by year | Pass | Pass | Correct counts; initial SQL omitted deterministic ordering. |
| Institution publication ranking | Partial | Pass | "Most" initially produced only one row; an explicit top-10 request produced the correct ranking. |
| Open-access percentage by year | Pass with presentation issue | Pass | Arithmetic was correct; initial output was not rounded to two decimals. |
| Primary-topic publication and citation impact | Pass with presentation issue | Pass | Joins, primary-topic filter, aggregation, and ranking were correct; one average was not rounded. |
| Authors and institutions for a named paper | Fail | Pass after prompt refinement | The initial SQL referenced `institution_id` on `work_authors`. Explicit affiliation guidance produced all eight expected author-institution rows. |

Final semantic result: **5/5 scenarios produced correct executable answers
after prompt refinement.**

This is not reported as 100% zero-shot accuracy. The initial run contained one
failure, one partial answer, and two presentation-quality issues. Preserving
that distinction makes the evaluation reproducible and honest.

## Safety coverage

Automated tests verify that ResearchLens rejects:

- `DELETE`, `UPDATE`, `DROP`, and other non-query operations;
- multiple SQL statements;
- unknown tables;
- external file and network functions such as `read_csv_auto`;
- invalid result limits; and
- repeated execution failures after the single allowed correction.

Generated SQL is parsed before execution and DuckDB is opened in read-only
mode. A prompt instruction alone is never treated as a security boundary.

## Reflection finding

DuckDB correctly detected an invalid model-generated column relationship that
was syntactically safe. ResearchLens now sends the failed SQL and database error
back to the model for exactly one correction attempt. The retry is bounded and
the corrected SQL passes through the same safety validation.

The first live correction attempt repeated the error, which exposed a 3B-model
limitation and motivated clearer schema guidance. The strengthened initial
prompt subsequently solved the four-table question in one attempt.

## Known limitations

- The 300-work dataset is useful for a local portfolio demo but is still too
  small for general research-market conclusions.
- The evaluation set contains seven questions and should be expanded before
  any production-quality accuracy claim.
- Numeric presentation can vary across model generations.
- Equivalent SQL may differ in complexity, ordering, and aliases.
- Latency depends strongly on local CPU/GPU allocation and whether the model is
  already loaded.
