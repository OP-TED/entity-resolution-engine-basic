"""Entity resolution service - public API for resolving entity mentions to clusters."""

import hashlib
import threading
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


# Module-level service registry - per entity type
_services: dict[str, EntityResolutionService] = {}
_entity_mappings: dict | None = None
_lock: threading.Lock = threading.Lock()

# Configuration
_ENTITY_FIELDS = ["legal_name", "country_code"]


def _reset_services() -> None:
    """Clear all service instances. Called from test fixtures for scenario isolation."""
    global _services, _entity_mappings
    with _lock:
        _services = {}
        _entity_mappings = None


def _resolve_config_path() -> Path:
    """Resolve the path to resolver.yaml relative to this module."""
    return Path(__file__).parent.parent.parent.parent / "config" / "resolver.yaml"


def _build_service() -> EntityResolutionService:
    """
    Factory: build and wire EntityResolutionService with all dependencies.

    Uses :memory: DuckDB for BDD tests. Production would use file-backed persistence.
    """
    config_path = _resolve_config_path()
    with open(config_path) as f:
        raw_config = yaml.safe_load(f)

    resolver_config = ResolverConfig.from_dict(raw_config)
    con = duckdb.connect(":memory:")
    init_schema(con, _ENTITY_FIELDS)

    mention_repo = DuckDBMentionRepository(con, _ENTITY_FIELDS)
    similarity_repo = DuckDBSimilarityRepository(con)
    cluster_repo = DuckDBClusterRepository(con)
    linker = SpLinkSimilarityLinker(_ENTITY_FIELDS, raw_config)

    return EntityResolutionService(
        mention_repo, similarity_repo, cluster_repo, linker, resolver_config
    )


def _get_service(entity_type: str) -> EntityResolutionService:
    """Get or create a service for the given entity type."""
    if entity_type not in _services:
        with _lock:
            if entity_type not in _services:
                _services[entity_type] = _build_service()
    return _services[entity_type]


def _get_entity_mappings() -> dict:
    """Lazily load and cache the RDF mapping config from config/rdf_mapping.yaml."""
    global _entity_mappings
    if _entity_mappings is None:
        with _lock:
            if _entity_mappings is None:
                mapping_path = (
                    Path(__file__).parent.parent.parent.parent
                    / "config"
                    / "rdf_mapping.yaml"
                )
                _entity_mappings = load_entity_mappings(mapping_path)
    return _entity_mappings


def _derive_mention_id(source_id: str, request_id: str, entity_type: str) -> str:
    """
    Derive a stable MentionId from source_id, request_id, and entity_type.

    Per ERE spec section 4, the mention ID is deterministic and reproducible.
    """
    raw = source_id + request_id + entity_type
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _resolve_to_result(entity_mention: EntityMention):
    """
    Core resolution logic: RDF parse/map, domain object construction, service invocation.

    Returns a ResolutionResult (domain type) which can be mapped to different response types
    (ClusterReference for resolve_entity_mention, full candidates list for protocol path).

    Args:
        entity_mention: EntityMention from erspec.

    Returns:
        ResolutionResult: Domain object with (cluster_id, score) candidates.

    Raises:
        ValueError: If RDF parsing fails, mapping fails, or entity type is unknown.
    """
    eid = entity_mention.identifiedBy
    service = _get_service(eid.entity_type)
    mention_id = MentionId(
        value=_derive_mention_id(eid.source_id, eid.request_id, eid.entity_type)
    )

    # Idempotency: if already resolved, return current state (re-runs _gen_cand)
    cached = service.find_cluster_for(mention_id)
    if cached is not None:
        return cached

    # Load RDF mapping config; raises ValueError for unknown entity types
    entity_mappings = _get_entity_mappings()
    entity_type_config = entity_mappings.get(eid.entity_type)
    if entity_type_config is None:
        raise ValueError(
            f"No rdf_mapping configured for entity_type '{eid.entity_type}'"
        )

    # Parse + map: ValueError propagates as-is to caller
    attributes = extract_mention_attributes(entity_mention.content, entity_type_config)
    mention = Mention(id=mention_id, attributes=attributes)
    return service.resolve(mention)


def resolve_entity_mention(entity_mention: EntityMention) -> ClusterReference:
    """
    Resolve an entity mention to a Cluster.

    This is the public API: takes an EntityMention from erspec, returns a single
    ClusterReference (the top candidate).

    Args:
        entity_mention: EntityMention with identifiedBy and content (Turtle RDF).

    Returns:
        ClusterReference with cluster_id, confidence_score, similarity_score.

    Raises:
        ValueError: If RDF parsing fails, mapping fails, or entity type is unknown.
    """
    result = _resolve_to_result(entity_mention)
    top = result.top
    # confidence_score = similarity_score = top.score
    # For singleton founders (no prior mentions), top.score = 0.0.
    # 0.0 reflects genuine uncertainty: the cluster is unconfirmed (single member).
    # TODO: distinguish confidence_score from similarity_score per ERE spec (P8.5)
    return ClusterReference(
        cluster_id=top.cluster_id.value,
        confidence_score=top.score,
        similarity_score=top.score,
    )
