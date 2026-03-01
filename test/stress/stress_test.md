# Stress Test Documentation

Unified stress test runner for the entity resolver. This document describes usage patterns, parameters, and interpretation of results.

## Quick Start

### Basic smoke test (100 records, ~5 seconds)

```bash
poetry run python3 test/stress_test.py \
  --dataset test/data/stress/mentions_100a.csv \
  --seed 20 \
  --records 30 \
  --output /tmp/results.json
```

### Cold-start test (no training, ~4 seconds)

```bash
poetry run python3 test/stress_test.py \
  --dataset test/data/stress/mentions_100a.csv \
  --no-train \
  --records 30 \
  --output /tmp/coldstart.json
```

### Standard baseline (1000 records, ~2-3 minutes)

```bash
poetry run python3 test/stress_test.py \
  --dataset test/data/stress/mentions_1000.csv \
  --seed 200 \
  --records 500 \
  --output /tmp/baseline.json
```

### Balanced clustering test

```bash
poetry run python3 test/stress_test.py \
  --dataset test/data/stress/mentions_100b.csv \
  --seed 20 \
  --records 50 \
  --output /tmp/balanced.json
```

### High-diversity geography test

```bash
poetry run python3 test/stress_test.py \
  --dataset test/data/stress/mentions_100c.csv \
  --seed 20 \
  --records 50 \
  --output /tmp/diverse_geo.json
```

## CLI Parameters

### Required

**`--dataset PATH`**
- Path to CSV file with stress test data
- Available: `test/data/stress/mentions_100a.csv`, `mentions_100b.csv`, `mentions_100c.csv`, `mentions_1000.csv`

### Optional

**`--config PATH`**
- Path to resolver config YAML (default: `config/resolver.yaml`)
- Determines blocking rules, thresholds, and Splink settings

**`--seed N`**
- Number of mentions to seed resolver with before stress loop (default: 200)
- Higher seed = warmer start, more stable latency
- Lower seed = cold-start behavior, variable latency

**`--records N`**
- Number of records to process in stress loop
- If omitted, processes all remaining records (after seed)

**`--time SECONDS`**
- Instead of fixed record count, run stress loop for N seconds
- Mutually exclusive with `--records`
- Useful for capacity planning: "How many records in 60 seconds?"

**`--output PATH`**
- JSON file to save results (default: `/tmp/stress_result.json`)

**`--name STR`**
- Experiment name (default: dataset basename, e.g., `mentions_100b`)

**`--no-train`**
- Skip training; use cold-start parameters only (forces `--seed 0`)
- Tests resolver behavior with only Splink cold-start probabilities
- No EM training occurs; model uses hard-coded m/u values from config
- Useful for measuring pure latency baseline without training overhead

## Understanding Results

### Summary Output

```
======================================================================
Experiment: mentions_100b
======================================================================
Dataset: test/data/stress/mentions_100b.csv
Mentions: 100 total, 50 stressed
Seeding: 20 mentions

Clusters (ground-truth): 20
Cluster distribution: {1: 5, 2: 10, 3: 3, 4: 2, 5: 0}

Latency (ms):
  Mean:     145.32
  Median:   143.87
  Std:       12.45
  Min:      121.03
  P95:      168.19
  P99:      171.02
  Max:      175.45

Memory: 1.2 MB (peak)
Total time: 7.3 sec
======================================================================
```

### Key Metrics

**Clustering Quality** (based on ground-truth CSV labels)
- **Precision**: % of mentions assigned to the correct ground-truth cluster
  - High = resolver matches original cluster labels well
  - Low = resolver creates different cluster assignments (expected for new data)
- **Recall**: % of non-singleton ground-truth clusters that got at least one mention assigned
  - High = resolver links known cluster members together
  - Low = resolver fails to find linkages between known cluster members
- **F1 Score**: Harmonic mean of precision and recall (0.0-1.0)
  - Balanced quality metric: 0 = no correct assignments, 1 = perfect clustering

**Clusters**
- Ground-truth count: Number of unique `cluster_id` values in stressed portion
- Distribution: Histogram showing how many clusters have 1, 2, 3... mentions
  - Sparsity indicator: High singleton count = sparse dataset

**Latency (ms)**
- **Mean**: Average per-request time (typical case)
- **Median**: 50th percentile (robust to outliers)
- **Std**: Standard deviation (variability)
- **P95, P99**: 95th and 99th percentile (tail behavior)
- **Min, Max**: Range (watch for outliers suggesting GC or I/O stalls)

**Memory**
- Peak memory used during stress loop (MB)
- In-memory DuckDB + Splink DataFrame size
- Should remain stable; growth suggests memory leak

**Total time**
- Wall-clock seconds for stress loop
- Includes I/O, GC, all overhead
- Throughput = records / time

### JSON Schema

The JSON output has this structure:

```json
{
  "name": "experiment_name",
  "dataset_path": "test/data/stress/mentions_100b.csv",
  "n_mentions": 100,
  "n_records_stressed": 50,
  "n_seed": 20,
  "n_clusters": 20,
  "cluster_distribution": {"1": 14, "2": 3, "3": 2, "4": 1},
  "mean_latency_ms": 145.32,
  "median_latency_ms": 143.87,
  "p95_latency_ms": 168.19,
  "p99_latency_ms": 171.02,
  "min_latency_ms": 121.03,
  "max_latency_ms": 175.45,
  "stdev_latency_ms": 12.45,
  "peak_memory_mb": 1.2,
  "total_time_sec": 7.3,
  "ground_truth_clusters": 20,
  "clustering_precision": 0.45,
  "clustering_recall": 0.82,
  "clustering_f1": 0.588,
  "metrics": [
    {
      "record_idx": 20,
      "mention_id": "m00001234",
      "latency_ms": 145.67,
      "cluster_id": "cl000042",
      "n_candidates": 5,
      "score": 0.92
    },
    ...
  ]
}
```

## Datasets

### mentions_100a.csv — Sparsity Baseline

**Use case**: Edge case with high sparsity (94% singletons)

- 100 mentions, 97 clusters
- Useful for testing resolver behavior when most entities are unique
- Expected latency: 15-25ms per request (cold-start variable)
- Total time: < 5 seconds seed + train

**Example**:
```bash
poetry run python3 test/stress_test.py \
  --dataset test/data/stress/mentions_100a.csv \
  --seed 30 \
  --records 50
```

### mentions_100b.csv — Balanced Clustering

**Use case**: Realistic clustering workload with even distribution

- 100 mentions, 20 clusters (5 per cluster)
- Each cluster = 1 EU country (20 different countries)
- Tests resolver with well-defined matches and diverse geography
- Expected latency: 20-30ms per request
- Total time: < 5 seconds seed + train

**Example**:
```bash
poetry run python3 test/stress_test.py \
  --dataset test/data/stress/mentions_100b.csv \
  --seed 20 \
  --records 60
```

### mentions_100c.csv — High-Diversity Geography

**Use case**: Blocking rule stress test with sparse country distribution

- 100 mentions, 20 clusters (5 per cluster)
- 24 EU countries, randomly distributed
- Tests resolver when blocking rules create sparse, diverse buckets
- Expected latency: 20-30ms per request
- Total time: < 5 seconds seed + train

**Example**:
```bash
poetry run python3 test/stress_test.py \
  --dataset test/data/stress/mentions_100c.csv \
  --seed 20 \
  --records 60
```

### mentions_1000.csv — Scalability Test

**Use case**: Standard baseline for scalability evaluation

- 1000 mentions, 638 clusters (realistic sparsity)
- 27 EU countries, randomized distribution
- Tests resolver at realistic scale
- Expected latency: 100-200ms per request
- Total time: 2-3 minutes (seed 200 + stress 500+)

**Example**:
```bash
poetry run python3 test/stress_test.py \
  --dataset test/data/stress/mentions_1000.csv \
  --seed 200 \
  --records 500
```

## Cold-Start Testing

### What is Cold-Start?

Cold-start means resolving mentions **without prior training**. The resolver uses only:
- Cold-start m/u probabilities from config (hardcoded)
- No EM training
- No seeding (resolver empty)

Useful for:
- Measuring "out-of-the-box" latency (no training overhead)
- Baseline performance before any warm data
- Testing Splink linker startup cost

### Running Cold-Start Tests

```bash
# Pure cold-start: no seeding, no training
poetry run python3 test/stress_test.py \
  --dataset test/data/stress/mentions_100a.csv \
  --no-train \
  --records 30
```

The `--no-train` flag:
- Forces `--seed 0` (no seeding)
- Skips EM training
- Uses cold-start parameters from config YAML

### Expected Behavior

Cold-start results typically show:
- **Higher latency** than trained (no optimized parameters)
- **More variable latency** (P99 >> Mean, indicating higher uncertainty)
- **Lower clustering accuracy** (more false negatives)
- **Faster startup** (no EM training overhead)

Example output:
```
Experiment: mentions_100a_coldstart
Seeding: 0 mentions
Latency (ms):
  Mean:     226.54
  Median:   225.72
  P95:      272.27
  P99:      272.27
```

vs. trained (for comparison):
```
Experiment: mentions_100a
Seeding: 20 mentions
Latency (ms):
  Mean:     218.76
  Median:   219.37
  P95:      238.11
```

### Cold-Start vs Warm-Start Comparison

```bash
# Warm-start baseline
poetry run python3 test/stress_test.py \
  --dataset test/data/stress/mentions_100b.csv \
  --seed 50 \
  --records 50 \
  --output /tmp/warm.json

# Cold-start equivalent
poetry run python3 test/stress_test.py \
  --dataset test/data/stress/mentions_100b.csv \
  --no-train \
  --records 50 \
  --output /tmp/cold.json
```

Compare `mean_latency_ms` in both JSON files to measure training benefit.

## Exit Strategies

### Record-based (default)

Process a fixed number of records:

```bash
# Process exactly 100 records after seeding
python3 test/stress_test.py \
  --dataset test/data/stress/mentions_1000.csv \
  --seed 200 \
  --records 100
```

**Pros**:
- Deterministic (same input = same output)
- Good for regression testing and comparisons
- Reproducible across runs

**Cons**:
- May not reflect real-world time constraints

### Time-based

Process records for a fixed duration:

```bash
# Run for 60 seconds, process as many records as possible
python3 test/stress_test.py \
  --dataset test/data/stress/mentions_1000.csv \
  --seed 200 \
  --time 60
```

**Pros**:
- Reflects real-world SLA constraints
- Good for capacity planning
- Shows throughput under time pressure

**Cons**:
- Non-deterministic (latency affects record count)
- Harder to compare across runs

## Assumptions & Constraints

1. **In-memory DuckDB**: All data fits in RAM
   - Suitable for POC/testing (< 1GB)
   - Not for production (use file-backed DB or distributed)

2. **Single-threaded**: No parallelization
   - Conservative latency measurement (no contention)
   - Useful for baseline, not production throughput

3. **Cold Splink linker**: No pre-trained model
   - Uses cold-start parameters from config
   - EM training happens during seed phase
   - Latency may stabilize after first N records

4. **Ground-truth clusters**: Used for quality metrics only
   - CSV must include `cluster_id` column
   - Used to compute cluster distribution
   - Not used for resolver evaluation (resolver doesn't see it)

5. **Single config**: All experiments use one resolver config
   - To test different configs, run separate experiments
   - Results not comparable if configs differ

## Typical Workflow

### 1. Quick Smoke Test

Verify setup works:

```bash
poetry run python3 test/stress_test.py \
  --dataset test/data/stress/mentions_100a.csv \
  --seed 10 \
  --records 20 \
  --verbose
```

**Expected output**: < 10 seconds, mean latency 150-250ms

### 2. Baseline (mentions_100b)

Quick baseline with balanced clustering:

```bash
poetry run python3 test/stress_test.py \
  --dataset test/data/stress/mentions_100b.csv \
  --seed 20 \
  --records 50 \
  --output /tmp/baseline_100b.json
```

**Expected output**: < 15 seconds, mean latency 100-200ms

### 3. Scalability (mentions_1000)

Test with realistic data volume:

```bash
poetry run python3 test/stress_test.py \
  --dataset test/data/stress/mentions_1000.csv \
  --seed 200 \
  --records 300 \
  --output /tmp/scalability_1000.json
```

**Expected output**: 2-3 minutes, mean latency 100-300ms

### 4. Blocking Rule Variant (mentions_100c)

Test geographic diversity:

```bash
poetry run python3 test/stress_test.py \
  --dataset test/data/stress/mentions_100c.csv \
  --seed 20 \
  --records 50 \
  --output /tmp/diverse_geo.json
```

**Expected output**: < 15 seconds, mean latency 100-200ms

## Troubleshooting

**"ModuleNotFoundError: No module named 'ere'"**
- Run with `poetry run`: `poetry run python3 test/stress_test.py`

**"No such file: test/data/stress/mentions_100a.csv"**
- Check dataset path is correct
- Datasets must be in `/home/greg/PROJECTS/ERS/ere-basic/test/data/stress/`

**"Your model is not yet fully trained" warnings**
- Normal with small seed or sparse data
- Splink uses cold-start parameters for untrained levels
- More seed data improves training (try `--seed 100`)

**Latency spikes (P99 >> Mean)**
- May indicate GC pauses or I/O stalls
- Try on quieter system or increase seed size for stability
- Use `--verbose` to see detailed timing

**Memory grows over time**
- Check `peak_memory_mb` in JSON output
- If > 1GB with 1000 records, investigate for leaks
- Consider smaller seed or fewer records

## Next Steps

- [Blocking rules configuration](../config/resolver.yaml)
- [Entity resolution service](../src/ere/services/entity_resolution_service.py)
- [Splink linker implementation](../src/ere/adapters/splink_linker_impl.py)
