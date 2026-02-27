"""Concrete RDF mapper implementation for Turtle RDF extraction.

This adapter implements the RDFMapper port using the rdf_mapper utilities
for Turtle RDF parsing and attribute extraction per YAML configuration.
"""

import hashlib
from pathlib import Path

from erspec.models.core import EntityMention

from ere.adapters.rdf_mapper import load_entity_mappings, extract_mention_attributes
from ere.models.resolver import Mention, MentionId
from ere.services.rdf_mapper_port import RDFMapper


class TurtleRDFMapper(RDFMapper):
    """Concrete RDF mapper for Turtle RDF format."""

    def __init__(self):
        """Initialize the RDF mapper with configuration."""
        self._mappings = self._load_mappings()

    @staticmethod
    def _load_mappings() -> dict:
        """Load entity mappings from config/rdf_mapping.yaml."""
        mapping_path = Path(__file__).parent.parent.parent.parent / "config" / "rdf_mapping.yaml"
        return load_entity_mappings(mapping_path)

    def map_entity_mention_to_domain(self, entity_mention: EntityMention) -> Mention:
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
        entity_type_config = self._mappings.get(eid.entity_type)
        if entity_type_config is None:
            raise ValueError(
                f"No rdf_mapping configured for entity_type '{eid.entity_type}'"
            )

        mention_id = MentionId(
            value=self._derive_mention_id(eid.source_id, eid.request_id, eid.entity_type)
        )
        attributes = extract_mention_attributes(entity_mention.content, entity_type_config)
        return Mention(id=mention_id, attributes=attributes)

    @staticmethod
    def _derive_mention_id(source_id: str, request_id: str, entity_type: str) -> str:
        """
        Derive a stable MentionId from source_id, request_id, and entity_type.

        Per ERE spec section 4, the mention ID is deterministic and reproducible.
        """
        raw = source_id + request_id + entity_type
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()
