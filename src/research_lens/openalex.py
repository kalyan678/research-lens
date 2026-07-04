from __future__ import annotations

import time
from collections.abc import Iterator
from typing import Any

import httpx


class OpenAlexClient:
    base_url = "https://api.openalex.org"

    def __init__(self, api_key: str, timeout_seconds: float = 30.0) -> None:
        if not api_key:
            raise ValueError("An OpenAlex API key is required")

        self.api_key = api_key
        self.client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout_seconds,
            headers={"User-Agent": "ResearchLens/0.1"},
        )

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> OpenAlexClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(1, 4):
            response = self.client.get(path, params=params)
            if response.status_code not in {429, 500, 502, 503, 504}:
                response.raise_for_status()
                return response.json()

            if attempt == 3:
                response.raise_for_status()

            retry_after = response.headers.get("Retry-After")
            delay = float(retry_after) if retry_after else 2 ** (attempt - 1)
            time.sleep(min(delay, 10.0))

        raise RuntimeError("OpenAlex request failed unexpectedly")

    def iter_works(
        self,
        query: str,
        from_year: int,
        to_year: int,
        max_works: int,
    ) -> Iterator[dict[str, Any]]:
        if from_year > to_year:
            raise ValueError("from_year cannot be greater than to_year")
        if max_works < 1:
            raise ValueError("max_works must be positive")

        cursor = "*"
        yielded = 0

        while yielded < max_works:
            page_size = min(100, max_works - yielded)
            payload = self._get(
                "/works",
                {
                    "api_key": self.api_key,
                    "search": query,
                    "filter": (
                        f"from_publication_date:{from_year}-01-01,"
                        f"to_publication_date:{to_year}-12-31"
                    ),
                    "per-page": page_size,
                    "cursor": cursor,
                },
            )

            results = payload.get("results") or []
            if not results:
                return

            for work in results:
                yield work
                yielded += 1
                if yielded >= max_works:
                    return

            next_cursor = (payload.get("meta") or {}).get("next_cursor")
            if not next_cursor or next_cursor == cursor:
                return
            cursor = next_cursor
