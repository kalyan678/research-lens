"""Shared natural-language query service for CLI and web interfaces."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import duckdb
import httpx

from research_lens.agent import AgentQueryExecutionError, AgentResult, run_sql_agent
from research_lens.baseline import UnsupportedQuestionError, generate_baseline_sql
from research_lens.config import Settings
from research_lens.ollama import OllamaResponseError, generate_ollama_sql
from research_lens.sql_safety import UnsafeQueryError

Provider = Literal["baseline", "ollama"]


class QuestionRejectedError(RuntimeError):
    """Raised when a natural-language question cannot be answered safely."""


@dataclass(frozen=True)
class QuestionResponse:
    provider_label: str
    result: AgentResult


def answer_question(
    settings: Settings,
    question: str,
    provider: Provider,
    *,
    max_rows: int = 20,
) -> QuestionResponse:
    """Generate, validate, and execute SQL for one natural-language question."""

    if provider == "baseline":

        def generate(_prompt: str) -> str:
            return generate_baseline_sql(question)

        provider_label = "Deterministic baseline"
    elif provider == "ollama":
        base_url = settings.ollama_base_url
        if not base_url:
            raise QuestionRejectedError(
                "OLLAMA_BASE_URL is missing from .env. Choose the baseline "
                "or configure Ollama."
            )

        def generate(prompt: str) -> str:
            return generate_ollama_sql(
                prompt,
                base_url=base_url,
                model=settings.ollama_model,
                timeout_seconds=settings.ollama_timeout_seconds,
            )

        provider_label = f"Ollama ({settings.ollama_model})"
    else:
        raise QuestionRejectedError(f"Unsupported provider: {provider}")

    try:
        result = run_sql_agent(
            question,
            generate,
            settings.database_path,
            max_rows=max_rows,
        )
    except (
        duckdb.Error,
        httpx.HTTPError,
        AgentQueryExecutionError,
        OllamaResponseError,
        UnsupportedQuestionError,
        UnsafeQueryError,
        ValueError,
    ) as error:
        raise QuestionRejectedError(str(error)) from error

    return QuestionResponse(provider_label=provider_label, result=result)
