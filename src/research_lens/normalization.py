from __future__ import annotations

from datetime import date
from typing import Any

NormalizedBundle = dict[str, list[dict[str, Any]]]


def _openalex_id(value: str | None) -> str | None:
    if not value:
        return None
    return value.rsplit("/", maxsplit=1)[-1]


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value[:10])


def _topic_row(topic: dict[str, Any]) -> dict[str, Any] | None:
    topic_id = _openalex_id(topic.get("id"))
    if not topic_id:
        return None

    return {
        "id": topic_id,
        "display_name": topic.get("display_name") or "Unknown topic",
        "domain_name": (topic.get("domain") or {}).get("display_name"),
        "field_name": (topic.get("field") or {}).get("display_name"),
        "subfield_name": (topic.get("subfield") or {}).get("display_name"),
    }


def normalize_work(payload: dict[str, Any]) -> NormalizedBundle:
    work_id = _openalex_id(payload.get("id"))
    if not work_id:
        raise ValueError("OpenAlex work is missing its id")

    primary_source = ((payload.get("primary_location") or {}).get("source")) or {}
    source_id = _openalex_id(primary_source.get("id"))

    sources: list[dict[str, Any]] = []
    if source_id:
        sources.append(
            {
                "id": source_id,
                "display_name": primary_source.get("display_name") or "Unknown source",
                "source_type": primary_source.get("type"),
                "issn_l": primary_source.get("issn_l"),
                "host_organization": _openalex_id(primary_source.get("host_organization")),
            }
        )

    authors_by_id: dict[str, dict[str, Any]] = {}
    institutions_by_id: dict[str, dict[str, Any]] = {}
    work_authors: list[dict[str, Any]] = []
    work_author_institutions: list[dict[str, Any]] = []

    for authorship in payload.get("authorships") or []:
        author = authorship.get("author") or {}
        author_id = _openalex_id(author.get("id"))
        if not author_id:
            continue

        authors_by_id[author_id] = {
            "id": author_id,
            "display_name": author.get("display_name") or "Unknown author",
            "orcid": author.get("orcid"),
        }
        work_authors.append(
            {
                "work_id": work_id,
                "author_id": author_id,
                "author_position": authorship.get("author_position"),
                "is_corresponding": bool(authorship.get("is_corresponding")),
            }
        )

        for institution in authorship.get("institutions") or []:
            institution_id = _openalex_id(institution.get("id"))
            if not institution_id:
                continue
            institutions_by_id[institution_id] = {
                "id": institution_id,
                "display_name": institution.get("display_name") or "Unknown institution",
                "country_code": institution.get("country_code"),
                "institution_type": institution.get("type"),
            }
            work_author_institutions.append(
                {
                    "work_id": work_id,
                    "author_id": author_id,
                    "institution_id": institution_id,
                }
            )

    primary_topic_id = _openalex_id((payload.get("primary_topic") or {}).get("id"))
    topics_by_id: dict[str, dict[str, Any]] = {}
    work_topics: list[dict[str, Any]] = []

    for topic in payload.get("topics") or []:
        row = _topic_row(topic)
        if not row:
            continue
        topics_by_id[row["id"]] = row
        work_topics.append(
            {
                "work_id": work_id,
                "topic_id": row["id"],
                "score": topic.get("score"),
                "is_primary": row["id"] == primary_topic_id,
            }
        )

    open_access = payload.get("open_access") or {}
    work = {
        "id": work_id,
        "doi": payload.get("doi"),
        "title": payload.get("title") or payload.get("display_name") or "Untitled work",
        "publication_year": payload.get("publication_year"),
        "publication_date": _parse_date(payload.get("publication_date")),
        "work_type": payload.get("type"),
        "language": payload.get("language"),
        "cited_by_count": int(payload.get("cited_by_count") or 0),
        "is_open_access": bool(open_access.get("is_oa")),
        "open_access_status": open_access.get("oa_status"),
        "source_id": source_id,
        "openalex_updated_date": _parse_date(payload.get("updated_date")),
    }

    return {
        "sources": sources,
        "institutions": list(institutions_by_id.values()),
        "authors": list(authors_by_id.values()),
        "topics": list(topics_by_id.values()),
        "works": [work],
        "work_authors": work_authors,
        "work_author_institutions": work_author_institutions,
        "work_topics": work_topics,
    }

