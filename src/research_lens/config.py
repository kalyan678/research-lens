from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    database_path: Path
    openalex_api_key: str | None
    ollama_base_url: str | None
    ollama_model: str

    @classmethod
    def from_env(cls) -> Settings:
        load_dotenv()
        ollama_base_url = os.getenv("OLLAMA_BASE_URL", "").strip()

        return cls(
            database_path=Path(
                os.getenv("DATABASE_PATH", "data/research_lens.duckdb")
            ).expanduser(),
            openalex_api_key=os.getenv("OPENALEX_API_KEY") or None,
            ollama_base_url=ollama_base_url.rstrip("/") or None,
            ollama_model=os.getenv("OLLAMA_MODEL", "qwen3:8b"),
        )
