"""Phase 8.3 smoke test: verify resolver components wire together correctly."""

import duckdb
import tempfile
import yaml

from ere.models.resolver import MentionId, Mention
from ere.adapters.duckdb_schema import init_schema
from ere.adapters.duckdb_repositories import (
    DuckDBMentionRepository,
    DuckDBSimilarityRepository,
    DuckDBClusterRepository,
)
from ere.adapters.splink_linker_impl import SpLinkSimilarityLinker, build_tf_df
from ere.services.entity_resolution_service import EntityResolver
from ere.services.resolver_config import ResolverConfig


def test_resolver_full_integration():
    """Verify all resolver components work together end-to-end."""
    # Create temporary DuckDB connection
    con = duckdb.connect(":memory:")

    # Entity fields for this test
    entity_fields = ["legal_name", "country_code"]

    # Initialize schema
    init_schema(con, entity_fields)

    # Create repositories
    mention_repo = DuckDBMentionRepository(con, entity_fields)
    similarity_repo = DuckDBSimilarityRepository(con)
    cluster_repo = DuckDBClusterRepository(con)

    # Load config
    config = {
        "threshold": 0.5,
        "match_weight_threshold": -10,
        "top_n": 100,
        "cache_strategy": "tf_incremental",
        "auto_train_threshold": 0,  # Disable for test
        "splink": {
            "probability_two_random_records_match": 0.3,
            "comparisons": [
                {"type": "jaro_winkler", "field": "legal_name", "thresholds": [0.9, 0.8]},
                {"type": "exact_match", "field": "country_code"},
            ],
            "blocking_rules": ["country_code"],
            "cold_start": {
                "comparisons": {
                    "legal_name": {
                        "m_probabilities": [0.80, 0.10, 0.10],
                        "u_probabilities": [0.02, 0.05, 0.93],
                    },
                    "country_code": {
                        "m_probabilities": [0.90, 0.10],
                        "u_probabilities": [0.20, 0.80],
                    },
                }
            },
        },
    }
    resolver_config = ResolverConfig.from_dict(config)

    # Create linker
    linker = SpLinkSimilarityLinker(entity_fields, config)

    # Create resolver
    service = EntityResolver(
        mention_repo, similarity_repo, cluster_repo, linker, resolver_config
    )

    # Test: Resolve first mention (creates new cluster)
    m1 = Mention(mention_id="m1", legal_name="Acme Corp", country_code="US")
    result1 = service.resolve(m1)

    assert result1 is not None
    assert len(result1.candidates) >= 1
    assert result1.top.cluster_id.value == "m1"  # New singleton cluster
    assert mention_repo.count() == 1
    assert cluster_repo.count() == 1

    # Test: Resolve similar mention (should match first)
    m2 = Mention(mention_id="m2", legal_name="Acme Corp", country_code="US")
    result2 = service.resolve(m2)

    assert result2 is not None
    assert len(result2.candidates) >= 1
    # Should be assigned to m1's cluster
    assert cluster_repo.find_cluster_of(MentionId(value="m2")).value == "m1"
    assert mention_repo.count() == 2
    assert cluster_repo.count() == 1  # Still one cluster

    # Test: Resolve dissimilar mention (creates new cluster)
    m3 = Mention(mention_id="m3", legal_name="TechCorp Inc", country_code="US")
    result3 = service.resolve(m3)

    assert result3 is not None
    assert len(result3.candidates) >= 1
    # Should create new cluster
    assert cluster_repo.find_cluster_of(MentionId(value="m3")).value == "m3"
    assert mention_repo.count() == 3
    assert cluster_repo.count() == 2  # Two clusters now

    # Test: State introspection
    state = service.state()
    assert state.mention_count == 3
    assert state.cluster_count == 2
    assert len(state.cluster_membership) == 2

    print("✅ All smoke tests passed!")


if __name__ == "__main__":
    test_resolver_full_integration()
