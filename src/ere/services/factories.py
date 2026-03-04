"""Factory functions for service instantiation.

This module is responsible for constructing entity resolution components with
all their adapter dependencies. It lives in the services layer because it
orchestrates service-level concerns. The service layer receives fully-constructed
instances without knowing the concrete implementation details.
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
from ere.adapters.rdf_mapper_port import RDFMapper
from ere.adapters.splink_linker_impl import SpLinkSimilarityLinker
from ere.services.entity_resolution_service import EntityResolver, EntityResolutionService
from ere.services.resolver_config import ResolverConfig


def build_entity_resolver(
    entity_fields: list[str] = None,
    resolver_config_path: str | Path = None,
    duckdb_path: str = None,
) -> EntityResolver:
    """
    Factory: construct EntityResolver with all concrete adapter dependencies.

    This factory instantiates DuckDB repositories and Splink linker, wiring them
    together with configuration. The service layer never directly instantiates
    these concrete types; it receives them pre-built via dependency injection.

    Args:
        entity_fields: Field names for entity attributes (e.g. ["legal_name", "country_code"]).
                      If None, reads from resolver.yaml config.
        resolver_config_path: Path to resolver.yaml config file.
                             If None, uses default path.
        duckdb_path: Path to DuckDB file (overrides resolver.yaml duckdb.path).
                    If None, uses path from resolver.yaml config.

    Returns:
        Fully-constructed EntityResolver with DuckDB backend and Splink linker.
    """
    if resolver_config_path is None:
        config_path = Path(__file__).parent.parent.parent.parent / "infra" / "config" / "resolver.yaml"
    else:
        config_path = Path(resolver_config_path)

    with open(config_path, encoding="utf-8") as f:
        raw_config = yaml.safe_load(f)

    resolver_config = ResolverConfig.from_dict(raw_config)

    # Use entity_fields from config; parameter overrides config if provided
    if entity_fields is None:
        entity_fields = resolver_config.entity_fields

    # Create DuckDB connection based on configured type
    if resolver_config.duckdb.type == "in-memory":  # pylint: disable=no-member  # Pydantic model attribute; pylint cannot resolve dynamically
        con = duckdb.connect(":memory:")
    elif resolver_config.duckdb.type == "persistent":  # pylint: disable=no-member  # Pydantic model attribute; pylint cannot resolve dynamically
        # DUCKDB_PATH env var takes precedence over the passed argument
        db_path = duckdb_path or resolver_config.duckdb.path  # pylint: disable=no-member  # Pydantic model attribute; pylint cannot resolve dynamically
        con = duckdb.connect(db_path)
    else:
        raise ValueError(
            f"Invalid duckdb type: {resolver_config.duckdb.type}. "  # pylint: disable=no-member  # Pydantic model attribute; pylint cannot resolve dynamically
            f"Must be 'in-memory' or 'persistent'."
        )

    init_schema(con, entity_fields)

    mention_repo = DuckDBMentionRepository(con, entity_fields)
    similarity_repo = DuckDBSimilarityRepository(con)
    cluster_repo = DuckDBClusterRepository(con)
    linker = SpLinkSimilarityLinker(entity_fields, raw_config)

    return EntityResolver(
        mention_repo, similarity_repo, cluster_repo, linker, resolver_config
    )


def build_entity_resolution_service(
    resolver: EntityResolver, mapper: RDFMapper
) -> EntityResolutionService:
    """
    Factory: construct EntityResolutionService with pre-built resolver and mapper.

    This factory wires the core resolver and RDF mapper together into the public
    API service, avoiding repeated instantiation on every request.

    Args:
        resolver: EntityResolver instance (pre-built core resolver).
        mapper: RDFMapper implementation (pre-built).

    Returns:
        Fully-constructed EntityResolutionService ready for request processing.
    """
    return EntityResolutionService(resolver, mapper)
