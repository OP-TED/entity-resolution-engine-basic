"""Splink-backed similarity linker adapter (concrete implementation of SimilarityLinker port)."""

from __future__ import annotations

import duckdb
import pandas as pd
import threading
from splink import Linker, SettingsCreator, block_on
import splink.comparison_library as cl
from splink.backends.duckdb import DuckDBAPI

from ere.models.resolver import Mention, MentionId, MentionLink
from ere.services.linker import SimilarityLinker


def build_tf_df(mentions: list[Mention], entity_fields: list[str]) -> pd.DataFrame:
    """
    Convert a list of Mention objects to a TF DataFrame suitable for Splink's initial_df.

    Empty list produces a zero-row DataFrame with pd.StringDtype() columns (required to avoid
    DuckDB integer-inference bug on empty DataFrames).

    Args:
        mentions: List of Mention objects to include in the search space.
        entity_fields: List of field names to extract from mentions (e.g. ["legal_name", "country_code"]).

    Returns:
        DataFrame with columns: mention_id, entity_fields..., __splink_salt.
    """
    cols = ["mention_id"] + entity_fields

    if not mentions:
        # Empty DataFrame: use pd.StringDtype() to avoid DuckDB integer-inference bug
        schema = {c: pd.array([], dtype=pd.StringDtype()) for c in cols}
        schema["__splink_salt"] = pd.array([], dtype="float64")
        return pd.DataFrame(schema)

    # Non-empty: build from mention data
    rows = []
    for mention in mentions:
        flat_dict = mention.to_flat_dict()
        row = {
            "mention_id": flat_dict["mention_id"],
            **{f: flat_dict.get(f) for f in entity_fields},
            "__splink_salt": 0.5,
        }
        rows.append(row)

    return pd.DataFrame(rows)


class SpLinkSimilarityLinker(SimilarityLinker):
    """
    Splink-backed implementation of SimilarityLinker port.

    Wraps Splink's Linker and maintains:
    - _splink_con: in-memory DuckDB connection (Splink temporary tables only)
    - _db_api: DuckDBAPI for Splink operations
    - _tf_df: in-memory DataFrame (search space of registered mentions)
    - _linker: Splink Linker instance

    Supports warm starts via initial_df parameter and incremental registration of new mentions.
    """

    def __init__(
        self,
        entity_fields: list[str],
        config: dict,
        initial_df: pd.DataFrame | None = None,
    ) -> None:
        """
        Initialize the Splink linker.

        Args:
            entity_fields: List of field names (e.g. ["legal_name", "country_code"]).
            config: Full resolver configuration dict (needs match_weight_threshold and splink section).
            initial_df: Pre-built TF DataFrame for warm starts; None means fresh (empty) start.
        """
        self._entity_fields = entity_fields
        self._config = config
        self._match_weight_threshold = config.get("match_weight_threshold", -10)

        # In-memory connection for Splink operations (avoids file I/O)
        self._splink_con = duckdb.connect()
        self._db_api = DuckDBAPI(connection=self._splink_con)

        # Initialize TF DataFrame from parameter or empty
        if initial_df is not None:
            self._tf_df = initial_df.copy()
        else:
            self._tf_df = build_tf_df([], entity_fields)

        # Create and initialize Splink linker
        settings = self._build_settings()
        self._linker = Linker(self._tf_df, settings, db_api=self._db_api)
        # Always register even when empty so Splink's cache has correct schema
        self._linker.table_management.register_table_input_nodes_concat_with_tf(
            self._tf_df, overwrite=True
        )

        # Apply cold-start parameters (before training)
        self._apply_cold_start_params()

        # Threading synchronization for safe linker swaps during training
        self._linker_swap_lock = threading.Lock()
        self._training_in_progress = threading.Event()

    def find_matches(self, mention: Mention) -> list[MentionLink]:
        """
        Score a mention against previously registered mentions.

        Returns all mention-links above match_weight_threshold (including below-threshold
        links needed for candidate discovery).

        Filters self-links (left_id == right_id) which can occur during warm-start
        when the mention already exists in the search space.

        Args:
            mention: The Mention to score against the search space.

        Returns:
            List of MentionLink objects (empty if no matches or search space is empty).
        """
        # Grab a local reference to the linker under lock to ensure we don't hold
        # the lock while Splink is running (which could block training threads).
        with self._linker_swap_lock:
            linker = self._linker

        # Splink's find_matches_to_new_records expects a list of dicts
        df = linker.inference.find_matches_to_new_records(
            [mention.to_flat_dict()],
            blocking_rules=self._get_blocking_rules(),
            match_weight_threshold=self._match_weight_threshold,
        ).as_pandas_dataframe()

        if df.empty:
            return []

        # Build MentionLink objects, filtering self-links
        links = []
        for _, row in df.iterrows():
            left_id = MentionId(value=str(row["mention_id_l"]))
            right_id = MentionId(value=str(row["mention_id_r"]))
            score = float(row["match_probability"])

            # Skip self-links (can occur in warm-start scenarios)
            if left_id == right_id:
                continue

            links.append(MentionLink(left_id=left_id, right_id=right_id, score=score))

        return links

    def register_mention(self, mention: Mention) -> None:
        """
        Add a mention to the search space for future find_matches() calls.

        Appends the mention to the TF DataFrame and re-registers it with Splink.
        Uses tf_incremental strategy (append only, no reload from database).

        Args:
            mention: The Mention to add to the search space.
        """
        flat_dict = mention.to_flat_dict()

        # Build new row with same schema as _tf_df
        new_row = pd.DataFrame([{
            "mention_id": flat_dict["mention_id"],
            **{f: flat_dict.get(f) for f in self._entity_fields},
            "__splink_salt": 0.5,
        }])

        # Cast string columns to pd.StringDtype() to prevent type drift on None values
        for col in self._entity_fields:
            if col in new_row.columns:
                new_row[col] = new_row[col].astype(pd.StringDtype())

        # Append to search space
        self._tf_df = pd.concat([self._tf_df, new_row], ignore_index=True)

        # Re-register with Splink
        self._linker.table_management.register_table_input_nodes_concat_with_tf(
            self._tf_df, overwrite=True
        )

    def train(self) -> None:
        """
        Estimate model parameters via EM (non-blocking, thread-safe).

        Safe to call multiple times (retraining is idempotent). Prevents concurrent
        training runs via _training_in_progress event.

        Uses copy-then-swap pattern: snapshots current TF DataFrame, trains on a new
        Linker instance, then swaps under lock. This allows find_matches() calls to
        proceed with the current linker while training happens asynchronously.

        Training failures (e.g., insufficient data for convergence) are caught silently,
        leaving cold-start defaults intact.
        """
        # Prevent concurrent training runs
        if self._training_in_progress.is_set():
            return
        self._training_in_progress.set()
        try:
            self._train_safe()
        finally:
            self._training_in_progress.clear()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_blocking_rules(self) -> list:
        """Build Splink blocking rule objects from config."""
        rules = []
        for rule in self._config["splink"]["blocking_rules"]:
            fields = rule if isinstance(rule, list) else [rule]
            rules.append(block_on(*fields))
        return rules

    def _build_settings(self) -> SettingsCreator:
        """Translate the config dict into a Splink SettingsCreator."""
        splink_cfg = self._config["splink"]

        comparisons = []
        for comp in splink_cfg["comparisons"]:
            if comp["type"] == "jaro_winkler":
                thresholds = comp.get("thresholds", [0.9, 0.8])
                comparisons.append(cl.JaroWinklerAtThresholds(comp["field"], thresholds))
            elif comp["type"] == "exact_match":
                comparisons.append(cl.ExactMatch(comp["field"]))
            else:
                raise ValueError(f"Unknown comparison type: {comp['type']!r}")

        kwargs = dict(
            link_type="dedupe_only",
            unique_id_column_name="mention_id",
            comparisons=comparisons,
            blocking_rules_to_generate_predictions=self._get_blocking_rules(),
        )
        prior = self._config["splink"].get("probability_two_random_records_match")
        if prior is not None:
            kwargs["probability_two_random_records_match"] = prior

        return SettingsCreator(**kwargs)

    def _get_em_training_rule(self):
        """
        Derive the EM training rule from config.

        Uses the first blocking rule, extracting the first field if it's a list
        (compound rule). This ensures EM training matches the blocking strategy.

        For config.yaml: first rule is "country_code" → block_on("country_code")
        For config_compound.yaml: first rule is [country_code, city] → block_on("country_code")
        For config_multirule.yaml: first rule is "country_code" → block_on("country_code")
        """
        first_rule = self._config["splink"]["blocking_rules"][0]
        em_field = first_rule[0] if isinstance(first_rule, list) else first_rule
        return block_on(em_field)

    def _train_safe(self) -> None:
        """
        Thread-safe training via copy-then-swap pattern.

        1. Snapshot the current TF DataFrame (may grow during training).
        2. Create a new Linker on a fresh in-memory DuckDB connection.
        3. Run EM training on the new linker.
        4. Re-register the current (possibly grown) TF DataFrame.
        5. Swap the linker reference under lock.

        Training failures are caught silently, leaving cold-start defaults intact.
        """
        try:
            # Snapshot current TF DataFrame at training start
            tf_df_snapshot = self._tf_df.copy()

            # Create new linker on fresh in-memory connection (no shared state)
            splink_con_new = duckdb.connect()
            db_api_new = DuckDBAPI(connection=splink_con_new)
            settings = self._build_settings()
            linker_new = Linker(tf_df_snapshot, settings, db_api=db_api_new)
            linker_new.table_management.register_table_input_nodes_concat_with_tf(
                tf_df_snapshot, overwrite=True
            )

            # Run EM training on the new linker
            linker_new.training.estimate_u_using_random_sampling(max_pairs=1e6)
            linker_new.training.estimate_parameters_using_expectation_maximisation(
                self._get_em_training_rule(), estimate_without_term_frequencies=True
            )

            # Re-register current TF DataFrame (which may have grown during training)
            linker_new.table_management.register_table_input_nodes_concat_with_tf(
                self._tf_df, overwrite=True
            )

            # Swap linker reference under lock (held for microseconds only)
            with self._linker_swap_lock:
                self._linker = linker_new
                self._splink_con = splink_con_new
                self._db_api = db_api_new

        except Exception:
            # Training failure: silently ignore, cold-start defaults remain active
            pass

    def _apply_cold_start_params(self) -> None:
        """
        Apply cold-start m/u probability defaults to Splink linker.

        Reads splink.cold_start.comparisons from config and sets m/u probabilities
        on each comparison level in the linker's settings object.

        If cold_start section is absent, uses Splink's built-in defaults.

        Skips null levels (Splink's internal null-value handling level).
        """
        # Check if cold_start config exists
        cold_start_cfg = self._config.get("splink", {}).get("cold_start", {})
        if not cold_start_cfg:
            return

        comparisons_cfg = cold_start_cfg.get("comparisons", {})
        if not comparisons_cfg:
            return

        # Iterate through comparison levels and apply m/u probabilities
        for idx, comparison in enumerate(self._linker._settings_obj.comparisons):
            # Get the field name from the comparison
            field_name = None
            if hasattr(comparison, 'output_column_name'):
                field_name = comparison.output_column_name
            elif hasattr(comparison, '_field_names') and comparison._field_names:
                field_name = comparison._field_names[0]

            if field_name not in comparisons_cfg:
                continue

            field_cfg = comparisons_cfg[field_name]

            # Apply m-probabilities to non-null levels
            if 'm_probabilities' in field_cfg:
                m_probs = field_cfg['m_probabilities']
                for level_idx, m_prob in enumerate(m_probs):
                    if level_idx < len(comparison.comparison_levels):
                        level = comparison.comparison_levels[level_idx]
                        # Skip null levels (Splink's internal null-value handling)
                        if hasattr(level, 'is_null_level') and level.is_null_level:
                            continue
                        try:
                            level.m_probability = m_prob
                        except (AttributeError, ValueError):
                            # If setting fails, skip this level gracefully
                            pass

            # Apply u-probabilities to non-null levels
            if 'u_probabilities' in field_cfg:
                u_probs = field_cfg['u_probabilities']
                for level_idx, u_prob in enumerate(u_probs):
                    if level_idx < len(comparison.comparison_levels):
                        level = comparison.comparison_levels[level_idx]
                        # Skip null levels
                        if hasattr(level, 'is_null_level') and level.is_null_level:
                            continue
                        try:
                            level.u_probability = u_prob
                        except (AttributeError, ValueError):
                            # If setting fails, skip this level gracefully
                            pass
