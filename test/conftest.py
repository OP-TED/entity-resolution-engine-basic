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
    with open(cfg_path) as f:
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
