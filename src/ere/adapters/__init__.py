from abc import abstractmethod
from typing import Protocol

from erspec.models.ere import ERERequest, EREResponse

from ere.adapters.duckdb_repositories import (
    DuckDBClusterRepository,
    DuckDBMentionRepository,
    DuckDBSimilarityRepository,
)
from ere.adapters.duckdb_schema import init_schema
from ere.adapters.repositories import (
    ClusterRepository,
    MentionRepository,
    SimilarityRepository,
)
from ere.adapters.splink_linker_impl import SpLinkSimilarityLinker, build_tf_df


class AbstractResolver(Protocol):
    """
          ERE resolver abstraction.

          An ERE resolver deals with the core of the job, ie, it takes requests like
    :class:`ere.models.core.ERERequest` and computes results for them.

          A resolver doesn't deal with aspects like networking or asynchronous processing, this
          is are concerns for services and entrypoints, which wrap around resolvers.

          As you can see, it makes sense to define resolvers as :class:`Protocol` classes, so that,
          for instance, even a simple lambda could be uses as a resolver.
    """

    @abstractmethod
    def process_request(self, request: ERERequest) -> EREResponse:
        """
        Resolves an entity resolution request, returning the corresponding response.

        This only concerns the resolution logic, leaving out aspects like transport or
        asynchronous processing.

        This should take care of wrapping exceptions into ErrorResponse results.
        """

    def __call__(self, request: ERERequest) -> EREResponse:
        return self.process_request(request)


__all__ = [
    "AbstractResolver",
    "build_tf_df",
    "ClusterRepository",
    "DuckDBClusterRepository",
    "DuckDBMentionRepository",
    "DuckDBSimilarityRepository",
    "init_schema",
    "MentionRepository",
    "SimilarityRepository",
    "SpLinkSimilarityLinker",
]
