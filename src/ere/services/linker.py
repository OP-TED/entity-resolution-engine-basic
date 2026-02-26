"""Similarity linker port interface (abstract base class).

This ABC defines the external dependency for pairwise similarity scoring
(e.g. Splink). The algorithm (EntityResolutionService) depends only on this
port, not on concrete implementations. This enables testing with stub linkers
and swapping the matching algorithm without changing service logic.
"""

from abc import ABC, abstractmethod

from ere.models.resolver import Mention, MentionLink


class SimilarityLinker(ABC):
    """
    Port: external dependency for pairwise similarity scoring (e.g. Splink).

    Responsibilities:
    - Score a new mention against previously registered mentions
    - Train the scoring model (EM, estimate parameters)
    - Maintain the search space of mention records
    """

    @abstractmethod
    def find_matches(self, mention: Mention) -> list[MentionLink]:
        """
        Score a mention against previously registered mentions.

        Returns all mention-links (pairs) above match_weight_threshold,
        regardless of cluster threshold. Below-threshold links are included
        so they can be used for candidate discovery in genCand().

        Args:
            mention: The Mention to score against the search space.

        Returns:
            List of MentionLink objects. Empty if no candidates exist or
            all pairs are below match_weight_threshold.
        """
        ...

    @abstractmethod
    def register_mention(self, mention: Mention) -> None:
        """
        Add a mention to the search space for future find_matches() calls.

        After this call, future find_matches() invocations will include this
        mention as a candidate for scoring.

        Args:
            mention: The Mention to add to the search space.
        """
        ...

    @abstractmethod
    def train(self) -> None:
        """
        Estimate model parameters via EM or other training algorithm.

        Safe to call multiple times (retraining is idempotent).
        Implementations handle insufficient data gracefully (e.g., via cold-start defaults).
        """
        ...
