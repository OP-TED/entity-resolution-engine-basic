"""Entity resolution service - public API for resolving entity mentions to clusters."""

from erspec.models.core import EntityMention, ClusterReference

from ere.models.resolver import Mention
from ere.services.entity_resolution_service import EntityResolutionService
from ere.services.rdf_mapper_port import RDFMapper


def resolve_to_result(
    entity_mention: EntityMention,
    service: EntityResolutionService,
    mapper: RDFMapper,
):
    """
    Core resolution pipeline: RDF parsing -> domain mapping -> service resolution.

    Used by both public API and adapter paths.

    Args:
        entity_mention: EntityMention from erspec.
        service: EntityResolutionService instance.
        mapper: RDFMapper implementation for entity mention parsing.

    Returns:
        ResolutionResult: Domain object with (cluster_id, score) candidates.

    Raises:
        ValueError: If RDF parsing fails or entity type is unknown.
    """
    mention = mapper.map_entity_mention_to_domain(entity_mention)

    # Idempotency: if already resolved, return current state
    cached = service.find_cluster_for(mention.id)
    if cached is not None:
        return cached

    return service.resolve(mention)


def resolve_entity_mention(
    entity_mention: EntityMention, service: EntityResolutionService = None, mapper: RDFMapper = None
) -> ClusterReference:
    """
    Resolve an entity mention to a Cluster (public API - returns top candidate).

    Args:
        entity_mention: EntityMention with identifiedBy and content (Turtle RDF).
        service: EntityResolutionService instance. If None, raises ValueError.
                 (In tests, inject the fixture; in production, use resolver adapter factory)
        mapper: RDFMapper implementation. If None, raises ValueError.
                (In tests, inject the fixture; in production, use resolver adapter factory)

    Returns:
        ClusterReference with cluster_id, confidence_score, similarity_score.

    Raises:
        ValueError: If RDF parsing fails, mapping fails, service/mapper is None, or entity type is unknown.
    """
    if service is None:
        raise ValueError(
            "service must be provided (inject EntityResolutionService fixture in tests, "
            "or use build_resolution_service() factory in production)"
        )
    if mapper is None:
        raise ValueError(
            "mapper must be provided (inject RDFMapper fixture in tests, "
            "or use build_resolution_service() factory in production)"
        )

    result = resolve_to_result(entity_mention, service, mapper)
    top = result.top

    # For singleton founders (no prior mentions), top.score = 0.0.
    # 0.0 reflects genuine uncertainty: the cluster is unconfirmed (single member).
    return ClusterReference(
        cluster_id=top.cluster_id.value,
        confidence_score=top.score,
        similarity_score=top.score,
    )
