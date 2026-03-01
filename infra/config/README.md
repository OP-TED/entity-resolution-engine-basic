# Resolver Configuration

This directory contains resolver configuration files for different blocking strategies.

## Files

- **resolver.yaml** — Standard configuration with single-field blocking (country_code)
- **resolver_compound.yaml** — Compound blocking rule (country_code AND city)
- **resolver_multirule.yaml** — Multi-rule blocking evaluated as union (country OR city OR name)

## Choosing a Configuration

**resolver.yaml (default):**
- Simple, single-field blocking on country_code
- Suitable for basic entity resolution with geographic partitioning
- Balanced precision/recall for most use cases

**resolver_compound.yaml:**
- Requires both country_code AND city to match before comparing
- Creates tight blocks with city-level granularity
- Trade-off: reduces pair volume (faster) but may miss cross-city variants

**resolver_multirule.yaml:**
- Three independent rules evaluated as OR: same country, OR same city, OR exact name match
- Broader coverage; picks up cross-country matches and exact duplicates
- Trade-off: more pairs per call (slower) but higher recall for diverse datasets

## Configuration Fields

All configs support:
- `threshold`: Cluster assignment probability cutoff (0.0-1.0)
- `match_weight_threshold`: Pre-filter for stored similarity pairs
- `top_n`: Maximum candidate clusters returned per resolution
- `cache_strategy`: Search space caching strategy (tf_incremental)
- `auto_train_threshold`: Mention count at which to trigger background EM training
- `splink`: Splink-specific settings (prior, comparisons, blocking rules, cold-start defaults)

See inline YAML comments for calibration guidance.
