"""Resolver configuration: typed extraction from YAML."""

from pydantic import BaseModel, ConfigDict


class ResolverConfig(BaseModel):
    """
    Typed resolver configuration extracted from YAML dict.

    Attributes:
        threshold: Cluster assignment probability cutoff (0.0-1.0).
                   A mention joins an existing cluster only if match_probability >= threshold.
        match_weight_threshold: Splink output pre-filter (log-odds).
                                Controls which scored pairs are stored in the similarities table.
                                -10 includes pairs with match_probability >= ~0.001.
        top_n: Maximum number of cluster references returned per resolution request.
        cache_strategy: Strategy for maintaining Splink search space cache.
                       Default: "tf_incremental" (incremental cache updates).
        auto_train_threshold: Number of mentions at which to trigger background training.
                             Default: 50 (0 = disabled).
    """

    model_config = ConfigDict(frozen=True)

    threshold: float
    match_weight_threshold: float
    top_n: int
    cache_strategy: str = "tf_incremental"
    auto_train_threshold: int = 50

    @classmethod
    def from_dict(cls, d: dict) -> "ResolverConfig":
        """
        Load configuration from YAML-parsed dict.

        Args:
            d: Dict with keys: threshold, match_weight_threshold, top_n, cache_strategy (optional),
                              auto_train_threshold (optional).

        Returns:
            ResolverConfig instance.

        Raises:
            ValidationError: If required keys are missing or values are invalid.
        """
        return cls(
            threshold=d["threshold"],
            match_weight_threshold=d["match_weight_threshold"],
            top_n=d["top_n"],
            cache_strategy=d.get("cache_strategy", "tf_incremental"),
            auto_train_threshold=d.get("auto_train_threshold", 50),
        )
