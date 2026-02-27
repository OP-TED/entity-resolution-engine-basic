"""Entity resolution service - public API for resolving entity mentions to clusters."""

import hashlib
from pathlib import Path

import duckdb
import yaml
from erspec.models.core import EntityMention, ClusterReference

from ere.adapters.rdf_mapper import load_entity_mappings, extract_mention_attributes
from ere.adapters.duckdb_repositories import (
    DuckDBMentionRepository,
    DuckDBSimilarityRepository,
    DuckDBClusterRepository,
)
from ere.adapters.duckdb_schema import init_schema
from ere.adapters.splink_linker_impl import SpLinkSimilarityLinker
from ere.models.resolver import Mention, MentionId
from ere.services.entity_resolution_service import EntityResolutionService
from ere.services.resolver_config import ResolverConfig


def build_resolution_service(entity_fields: list[str] = None) -> EntityResolutionService:
    """
    Factory: build EntityResolutionService with all dependencies.

    Args:
        entity_fields: Field names for entity attributes (e.g. ["legal_name", "country_code"]).
                      If None, reads from resolver.yaml config.

    Returns:
        Configured EntityResolutionService instance.
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


def _derive_mention_id(source_id: str, request_id: str, entity_type: str) -> str:
    """
    Derive a stable MentionId from source_id, request_id, and entity_type.

    Per ERE spec section 4, the mention ID is deterministic and reproducible.
    """
    raw = source_id + request_id + entity_type
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _get_entity_mappings() -> dict:
    """Load the RDF mapping config from config/rdf_mapping.yaml."""
    mapping_path = Path(__file__).parent.parent.parent.parent / "config" / "rdf_mapping.yaml"
    return load_entity_mappings(mapping_path)


def map_entity_mention_to_domain(entity_mention: EntityMention) -> Mention:
    """
    Map EntityMention (erspec) to Mention (domain).

    Performs RDF parsing and attribute extraction per config.

    Args:
        entity_mention: EntityMention from erspec.

    Returns:
        Mention: Domain object with id and attributes.

    Raises:
        ValueError: If RDF parsing fails or entity type is unknown.
    """
    eid = entity_mention.identifiedBy
    entity_mappings = _get_entity_mappings()
    entity_type_config = entity_mappings.get(eid.entity_type)
    if entity_type_config is None:
        raise ValueError(
            f"No rdf_mapping configured for entity_type '{eid.entity_type}'"
        )

    mention_id = MentionId(
        value=_derive_mention_id(eid.source_id, eid.request_id, eid.entity_type)
    )
    attributes = extract_mention_attributes(entity_mention.content, entity_type_config)
    return Mention(id=mention_id, attributes=attributes)


def resolve_to_result(
    entity_mention: EntityMention, service: EntityResolutionService
):
    """
    Core resolution pipeline: RDF parsing -> domain mapping -> service resolution.

    Used by both public API and adapter paths.

    Args:
        entity_mention: EntityMention from erspec.
        service: EntityResolutionService instance.

    Returns:
        ResolutionResult: Domain object with (cluster_id, score) candidates.

    Raises:
        ValueError: If RDF parsing fails or entity type is unknown.
    """
    mention = map_entity_mention_to_domain(entity_mention)

    # Idempotency: if already resolved, return current state
    cached = service.find_cluster_for(mention.id)
    if cached is not None:
        return cached

    return service.resolve(mention)


def resolve_entity_mention(
    entity_mention: EntityMention, service=None
) -> ClusterReference:
    """
    Resolve an entity mention to a Cluster (public API - returns top candidate).

    Args:
        entity_mention: EntityMention with identifiedBy and content (Turtle RDF).
        service: EntityResolutionService instance. If None, raises ValueError.
                 (In tests, inject the fixture; in production, use resolver adapter)

    Returns:
        ClusterReference with cluster_id, confidence_score, similarity_score.

    Raises:
        ValueError: If RDF parsing fails, mapping fails, service is None, or entity type is unknown.
    """
    if service is None:
        raise ValueError(
            "service must be provided (inject EntityResolutionService fixture in tests, "
            "or use EntityResolutionResolver adapter in production)"
        )

    result = resolve_to_result(entity_mention, service)
    top = result.top

    # For singleton founders (no prior mentions), top.score = 0.0.
    # 0.0 reflects genuine uncertainty: the cluster is unconfirmed (single member).
    return ClusterReference(
        cluster_id=top.cluster_id.value,
        confidence_score=top.score,
        similarity_score=top.score,
    )
