"""Adapter: EntityResolutionResolver implements AbstractResolver for pub/sub service."""

from datetime import datetime, timezone

from erspec.models.core import ClusterReference, EntityMentionResolutionRequest
from erspec.models.ere import AbstractResolver, ERERequest, EREResponse, EREErrorResponse
from erspec.models.ere.entity_mention_resolution import EntityMentionResolutionResponse

from ere.adapters.factories import build_resolution_service, build_rdf_mapper
from ere.services.resolution import resolve_to_result


class EntityResolutionResolver(AbstractResolver):
    """
    Implements AbstractResolver for the pub/sub service path.

    Handles EntityMentionResolutionRequest -> EntityMentionResolutionResponse.
    Returns EREErrorResponse for unknown request types or resolution errors.

    Note: Builds fresh service instance per request. For production persistence,
    consider storing service as instance attribute and managing lifecycle separately.
    """

    def process_request(self, request: ERERequest) -> EREResponse:
        """
        Process a resolution request and return a response.

        Args:
            request: ERERequest (could be EntityMentionResolutionRequest or other type).

        Returns:
            EntityMentionResolutionResponse if request is EntityMentionResolutionRequest,
            EREErrorResponse for unknown request types or resolution errors.
        """
        now = datetime.now(timezone.utc)

        if not isinstance(request, EntityMentionResolutionRequest):
            return EREErrorResponse(
                ere_request_id=getattr(request, "ere_request_id", "unknown"),
                error_type="UnsupportedRequestType",
                error_title="Unsupported request type",
                error_detail=f"EntityResolutionResolver does not handle {type(request).__name__}",
                timestamp=now,
            )

        try:
            service = build_resolution_service()
            mapper = build_rdf_mapper()
            result = resolve_to_result(request.entity_mention, service, mapper)
            candidates = [
                ClusterReference(
                    cluster_id=c.cluster_id.value,
                    confidence_score=c.score,
                    similarity_score=c.score,
                )
                for c in result.candidates
            ]
            return EntityMentionResolutionResponse(
                entity_mention_id=request.entity_mention.identifiedBy,
                candidates=candidates,
                ere_request_id=request.ere_request_id,
                timestamp=now,
            )
        except Exception as exc:
            return EREErrorResponse(
                ere_request_id=request.ere_request_id,
                error_type=type(exc).__name__,
                error_title="Resolution error",
                error_detail=str(exc),
                timestamp=now,
            )

    def __call__(self, request: ERERequest) -> EREResponse:
        """Make the resolver callable."""
        return self.process_request(request)
