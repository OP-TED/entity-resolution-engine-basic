"""Factory functions for concrete adapter instantiation.

This module is responsible for instantiating concrete RDF mapper implementations.
It lives in the adapters layer because it owns the selection of concrete
implementations.

Services never import from here; they receive fully-constructed instances instead.
This keeps the service layer free of concrete adapter dependencies and makes
swapping implementations safe and testable.
"""

from pathlib import Path

from ere.adapters.rdf_mapper_impl import TurtleRDFMapper
from ere.adapters.rdf_mapper_port import RDFMapper


def build_rdf_mapper(rdf_mapping_path: str | Path = None) -> RDFMapper:
    """
    Factory: construct RDFMapper for entity mention parsing.

    Args:
        rdf_mapping_path: Path to rdf_mapping.yaml config file.
                         If None, uses default path.

    Returns:
        Fully-constructed RDFMapper implementation (TurtleRDFMapper).
    """
    return TurtleRDFMapper(rdf_mapping_path)
