from datetime import date

from research_lens.normalization import normalize_work


def test_normalize_work_builds_relational_bundle() -> None:
    payload = {
        "id": "https://openalex.org/W123",
        "doi": "https://doi.org/10.1000/example",
        "title": "A useful research paper",
        "publication_year": 2025,
        "publication_date": "2025-03-20",
        "type": "article",
        "language": "en",
        "cited_by_count": 42,
        "updated_date": "2026-01-02T10:30:00",
        "open_access": {"is_oa": True, "oa_status": "gold"},
        "primary_location": {
            "source": {
                "id": "https://openalex.org/S10",
                "display_name": "Example Journal",
                "type": "journal",
                "issn_l": "1234-5678",
                "host_organization": "https://openalex.org/P99",
            }
        },
        "authorships": [
            {
                "author": {
                    "id": "https://openalex.org/A1",
                    "display_name": "Ada Researcher",
                    "orcid": "https://orcid.org/0000-0000-0000-0001",
                },
                "author_position": "first",
                "is_corresponding": True,
                "institutions": [
                    {
                        "id": "https://openalex.org/I5",
                        "display_name": "Example University",
                        "country_code": "IN",
                        "type": "education",
                    }
                ],
            }
        ],
        "primary_topic": {"id": "https://openalex.org/T7"},
        "topics": [
            {
                "id": "https://openalex.org/T7",
                "display_name": "Language Models",
                "score": 0.91,
                "domain": {"display_name": "Physical Sciences"},
                "field": {"display_name": "Computer Science"},
                "subfield": {"display_name": "Artificial Intelligence"},
            }
        ],
    }

    bundle = normalize_work(payload)

    assert bundle["works"][0]["id"] == "W123"
    assert bundle["works"][0]["publication_date"] == date(2025, 3, 20)
    assert bundle["works"][0]["source_id"] == "S10"
    assert bundle["authors"][0]["id"] == "A1"
    assert bundle["institutions"][0]["id"] == "I5"
    assert bundle["work_authors"][0]["is_corresponding"] is True
    assert bundle["work_topics"][0] == {
        "work_id": "W123",
        "topic_id": "T7",
        "score": 0.91,
        "is_primary": True,
    }


def test_normalize_work_rejects_missing_id() -> None:
    try:
        normalize_work({"title": "No id"})
    except ValueError as error:
        assert "missing its id" in str(error)
    else:
        raise AssertionError("Expected normalize_work to reject a missing id")

