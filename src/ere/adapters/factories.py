"""Factory functions for concrete adapter instantiation.

This module is responsible for instantiating concrete adapter implementations
(DuckDB repositories, Splink linker, RDF mapper, etc.). It lives in the adapters
layer because it owns the selection and wiring of concrete implementations.

Services never import from here; they receive fully-constructed instances instead.
This keeps the service layer free of concrete adapter dependencies and makes
swapping implementations safe and testable.
"""

from pathlib import Path

import duckdb
import yaml

from ere.adapters.duckdb_repositories import (
    DuckDBClusterRepository,
    DuckDBMentionRepository,
    DuckDBSimilarityRepository,
)
from ere.adapters.duckdb_schema import init_schema
from ere.adapters.rdf_mapper_impl import TurtleRDFMapper
from ere.adapters.splink_linker_impl import SpLinkSimilarityLinker
from ere.services.entity_resolution_service import EntityResolutionService
from ere.services.resolver_config import ResolverConfig
from ere.services.rdf_mapper_port import RDFMapper


def build_resolution_service(entity_fields: list[str] = None) -> EntityResolutionService:
    """
    Factory: construct EntityResolutionService with all concrete adapter dependencies.

    This factory instantiates DuckDB repositories and Splink linker, wiring them
    together with configuration. The service layer never directly instantiates
    these concrete types; it receives them pre-built via dependency injection.

    Args:
        entity_fields: Field names for entity attributes (e.g. ["legal_name", "country_code"]).
                      If None, reads from resolver.yaml config.

    Returns:
        Fully-constructed EntityResolutionService with DuckDB backend and Splink linker.
    """
    if entity_fields is None:
        entity_fields = ["legal_name", "country_code"]

    config_path = Path(__file__).parent.parent.parent.parent / "config" / "resolver.yaml"
    with open(config_path) as f:
        raw_config = yaml.safe_load(f)

    resolver_config = ResolverConfig.from_dict(raw_config)
    con = duckdb.connect(":memory:")
    init_schema(con, entity_fields)

    mention_repo = DuckDBMentionRepository(con, entity_fields)
    similarity_repo = DuckDBSimilarityRepository(con)
    cluster_repo = DuckDBClusterRepository(con)
    linker = SpLinkSimilarityLinker(entity_fields, raw_config)

    return EntityResolutionService(
        mention_repo, similarity_repo, cluster_repo, linker, resolver_config
    )


def build_rdf_mapper() -> RDFMapper:
    """
    Factory: construct RDFMapper for entity mention parsing.

    Returns:
        Fully-constructed RDFMapper implementation (TurtleRDFMapper).
    """
    return TurtleRDFMapper()
