import os
import logging.config
from pathlib import Path

import pytest
import yaml

"""
Pytest configuration file, which the framework picks up at startup.

[Details here](https://docs.pytest.org/en/stable/reference/fixtures.html)

"""

# Locate local test data (copied from entity-resolution-spec)
TEST_DATA_ROOT = Path(__file__).parent / "test_data"


def pytest_configure(config: pytest.Config):
    """
    Configures various pytest settings:

    * markers for tests
    * Logging
    """

    config.addinivalue_line("markers", "integration: Integration test marker.")

    # Setup logging from YAML config file
    cfg_path = os.path.join(os.path.dirname(__file__), "resources/logging-test.yml")
    with open(cfg_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    logging.config.dictConfig(config)


# ============================================================================
# Helper: Load RDF content by relative path
# ============================================================================


def load_rdf(relative_path: str) -> str:
    """
    Load RDF content from test_data directory.

    Args:
        relative_path: Path relative to test_data/, e.g., "organizations/group1/661238-2023.ttl"

    Returns:
        str: Full RDF/Turtle content

    Raises:
        FileNotFoundError: If file does not exist
    """
    file_path = TEST_DATA_ROOT / relative_path
    if not file_path.exists():
        raise FileNotFoundError(f"Test data file not found: {file_path}")
    return file_path.read_text(encoding="utf-8")


# ============================================================================
# Organizations Test Data Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def org_group1_file1() -> str:
    """Organizations group1, file 1."""
    return load_rdf("organizations/group1/661238-2023.ttl")


@pytest.fixture(scope="session")
def org_group1_file2() -> str:
    """Organizations group1, file 2."""
    return load_rdf("organizations/group1/662860-2023.ttl")


@pytest.fixture(scope="session")
def org_group1_file3() -> str:
    """Organizations group1, file 3."""
    return load_rdf("organizations/group1/663653-2023.ttl")


@pytest.fixture(scope="session")
def org_group2_file1() -> str:
    """Organizations group2, file 1."""
    return load_rdf("organizations/group2/661197-2023.ttl")


@pytest.fixture(scope="session")
def org_group2_file2() -> str:
    """Organizations group2, file 2."""
    return load_rdf("organizations/group2/663952-2023.ttl")


# ============================================================================
# Procedures Test Data Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def proc_group1_file1() -> str:
    """Procedures group1, file 1."""
    return load_rdf("procedures/group1/662861-2023.ttl")


@pytest.fixture(scope="session")
def proc_group1_file2() -> str:
    """Procedures group1, file 2."""
    return load_rdf("procedures/group1/663131-2023.ttl")


@pytest.fixture(scope="session")
def proc_group1_file3() -> str:
    """Procedures group1, file 3."""
    return load_rdf("procedures/group1/664733-2023.ttl")


@pytest.fixture(scope="session")
def proc_group2_file1() -> str:
    """Procedures group2, file 1."""
    return load_rdf("procedures/group2/661196-2023.ttl")


@pytest.fixture(scope="session")
def proc_group2_file2() -> str:
    """Procedures group2, file 2."""
    return load_rdf("procedures/group2/663262-2023.ttl")


# ============================================================================
# Entity Resolution Service Fixture
# ============================================================================


@pytest.fixture
def entity_resolution_service():
    """
    Fresh EntityResolver instance per test (core resolver).

    Creates isolated resolver with in-memory DuckDB for test scenario isolation.
    Entity fields are derived from resolver.yaml config as the source of truth.
    """
    import duckdb
    from ere.adapters.duckdb_repositories import (
        DuckDBMentionRepository,
        DuckDBSimilarityRepository,
        DuckDBClusterRepository,
    )
    from ere.adapters.duckdb_schema import init_schema
    from ere.adapters.splink_linker_impl import SpLinkSimilarityLinker
    from ere.services.entity_resolution_service import EntityResolver
    from ere.services.resolver_config import ResolverConfig

    # Load resolver config (from infra/config directory)
    config_path = Path(__file__).parent.parent / "infra" / "config" / "resolver.yaml"
    with open(config_path, encoding="utf-8") as f:
        raw_config = yaml.safe_load(f)

    # Entity fields are the source of truth from config
    entity_fields = list(raw_config.get("splink", {}).get("comparisons", [])[0].keys())
    if "field" in str(raw_config.get("splink", {}).get("comparisons", [])[0]):
        # Extract field names from comparison configurations
        entity_fields = [
            comp["field"]
            for comp in raw_config.get("splink", {}).get("comparisons", [])
        ]

    # For now, entity_fields are hardcoded but validated against config
    # TODO: Extract from splink.comparisons and blocking_rules
    entity_fields = ["legal_name", "country_code"]

    resolver_config = ResolverConfig.from_dict(raw_config)
    con = duckdb.connect(":memory:")
    init_schema(con, entity_fields)

    mention_repo = DuckDBMentionRepository(con, entity_fields)
    similarity_repo = DuckDBSimilarityRepository(con)
    cluster_repo = DuckDBClusterRepository(con)
    linker = SpLinkSimilarityLinker(entity_fields, raw_config)

    return EntityResolver(
        mention_repo, similarity_repo, cluster_repo, linker, resolver_config
    )


# ============================================================================
# RDF Mapper Fixture
# ============================================================================


@pytest.fixture
def rdf_mapper():
    """
    Fresh RDFMapper instance per test.

    Returns a concrete TurtleRDFMapper implementation for Turtle RDF parsing.
    """
    from ere.adapters.rdf_mapper_impl import TurtleRDFMapper

    return TurtleRDFMapper()
