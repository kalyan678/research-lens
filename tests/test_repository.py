import duckdb

from research_lens.database import initialize_schema
from research_lens.normalization import normalize_work
from research_lens.repository import ResearchRepository


def _work_payload(work_id: str, institution_name: str) -> dict:
    return {
        "id": f"https://openalex.org/{work_id}",
        "title": f"Work {work_id}",
        "publication_year": 2025,
        "publication_date": "2025-01-01",
        "type": "article",
        "cited_by_count": 1,
        "open_access": {"is_oa": True, "oa_status": "gold"},
        "primary_location": {
            "source": {
                "id": "https://openalex.org/S1",
                "display_name": "Shared Source",
                "type": "journal",
            }
        },
        "authorships": [
            {
                "author": {
                    "id": f"https://openalex.org/A{work_id}",
                    "display_name": f"Author {work_id}",
                },
                "author_position": "first",
                "is_corresponding": True,
                "institutions": [
                    {
                        "id": "https://openalex.org/I56590836",
                        "display_name": institution_name,
                        "country_code": "IN",
                        "type": "education",
                    }
                ],
            }
        ],
        "topics": [],
    }


def test_repeated_parent_entities_can_be_updated() -> None:
    connection = duckdb.connect(":memory:")
    initialize_schema(connection)
    repository = ResearchRepository(connection)

    repository.upsert_work_bundle(
        normalize_work(_work_payload("W1", "Original Institution Name"))
    )
    repository.upsert_work_bundle(
        normalize_work(_work_payload("W2", "Updated Institution Name"))
    )

    assert connection.execute("SELECT COUNT(*) FROM works").fetchone() == (2,)
    assert connection.execute("SELECT COUNT(*) FROM institutions").fetchone() == (1,)
    assert connection.execute(
        "SELECT display_name FROM institutions WHERE id = 'I56590836'"
    ).fetchone() == ("Updated Institution Name",)
    assert connection.execute(
        """
        SELECT COUNT(*)
        FROM work_author_institutions wai
        JOIN institutions i ON i.id = wai.institution_id
        WHERE i.id = 'I56590836'
        """
    ).fetchone() == (2,)

    connection.close()
