

from erspec.models.core import EntityMention, ClusterReference


def resolve_entity_mention(entity_mention: EntityMention) -> ClusterReference:
    """
    Resolve an entity mention to a Cluster.
    TODO: This is a placeholder implementation that simply returns a dummy ClusterReference.

    The actual implementation would involve calling the ERS and processing the response to create a ClusterReference.
    """
    return ClusterReference(cluster_id="dummy_cluster_id", confidence_score=0.9, similarity_score=0.9)