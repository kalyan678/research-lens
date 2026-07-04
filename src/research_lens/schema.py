"""DuckDB schema for the normalized OpenAlex analytical model."""

SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS sources (
        id VARCHAR PRIMARY KEY,
        display_name VARCHAR NOT NULL,
        source_type VARCHAR,
        issn_l VARCHAR,
        host_organization VARCHAR
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS institutions (
        id VARCHAR PRIMARY KEY,
        display_name VARCHAR NOT NULL,
        country_code VARCHAR,
        institution_type VARCHAR
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS authors (
        id VARCHAR PRIMARY KEY,
        display_name VARCHAR NOT NULL,
        orcid VARCHAR
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS topics (
        id VARCHAR PRIMARY KEY,
        display_name VARCHAR NOT NULL,
        domain_name VARCHAR,
        field_name VARCHAR,
        subfield_name VARCHAR
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS works (
        id VARCHAR PRIMARY KEY,
        doi VARCHAR,
        title VARCHAR NOT NULL,
        publication_year INTEGER,
        publication_date DATE,
        work_type VARCHAR,
        language VARCHAR,
        cited_by_count INTEGER NOT NULL DEFAULT 0,
        is_open_access BOOLEAN NOT NULL DEFAULT FALSE,
        open_access_status VARCHAR,
        source_id VARCHAR,
        openalex_updated_date DATE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS work_authors (
        work_id VARCHAR,
        author_id VARCHAR,
        author_position VARCHAR,
        is_corresponding BOOLEAN NOT NULL DEFAULT FALSE,
        PRIMARY KEY (work_id, author_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS work_author_institutions (
        work_id VARCHAR,
        author_id VARCHAR,
        institution_id VARCHAR,
        PRIMARY KEY (work_id, author_id, institution_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS work_topics (
        work_id VARCHAR,
        topic_id VARCHAR,
        score DOUBLE,
        is_primary BOOLEAN NOT NULL DEFAULT FALSE,
        PRIMARY KEY (work_id, topic_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS works_publication_year_idx ON works(publication_year)",
    "CREATE INDEX IF NOT EXISTS works_cited_by_count_idx ON works(cited_by_count)",
    "CREATE INDEX IF NOT EXISTS institutions_country_code_idx ON institutions(country_code)",
]

CORE_TABLES = ("works", "authors", "institutions", "topics", "sources")
RELATIONSHIP_TABLES = (
    "work_authors",
    "work_author_institutions",
    "work_topics",
)
ALL_TABLES = CORE_TABLES + RELATIONSHIP_TABLES
