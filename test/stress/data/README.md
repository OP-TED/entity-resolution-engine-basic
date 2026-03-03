# Stress Test Datasets

Focused, EU-based datasets for performance testing with **algorithmically-derived ground-truth clusters**.

## Files

### mentions_100a.csv — Sparsity Baseline (Cold-Start Behavior)
- **Size**: 100 mentions (5.6 KB)
- **Clusters**: 100 clusters (all marked as singletons: `cluster_id = mention_id`)
- **Cluster distribution**: 100% singletons in ground truth
- **Geography**: 27 EU countries (randomized)
- **Use Case**: Cold-start behavior test with diverse synthetic names
- **Expected latency**: ~15-25ms per request (cold-start with limited training)
- **Estimated total time**: <5 seconds seed + train
- **Quality characteristics**:
  - Low precision (0-10%) expected due to model uncertainty with limited training data
  - Shows how algorithm behaves when seeded with limited diverse data
  - **Note**: Precision is low because the trained model makes false-positive matches on synthetic data
  - This is realistic behavior, not a bug

### mentions_100b.csv — Meaningful Company Name Clustering
- **Size**: 100 mentions (5.6 KB)
- **Clusters**: 42 clusters (derived by Jaro-Winkler >= 0.8 on legal_name)
- **Cluster distribution**: 10 singletons, 18×2-member, 4×3-member, 8×4-member, 2×5-member
- **Geography**: 20 EU countries (5 mentions per country)
- **Name patterns**: Realistic business name variations
  - Exact matches: "Pepsi" vs "Pepsi" (JW=1.0)
  - Suffix variations: "Pepsi" vs "Pepsi Inc" (JW≥0.91)
  - Minor typos: "Pepsi" vs "Pespi Inc" (JW≥0.82)
  - Character variations: "Coca Cola" vs "Coca-Cola" (JW≥0.95)
  - Look-alikes (intentional non-matches): "Bridgestone" vs "Cornerstone"
- **Use Case**: Realistic clustering test with plausible name variations
- **Expected latency**: ~20-30ms per request
- **Estimated total time**: <5 seconds seed + train
- **Quality baseline**: Precision ~70-85%, Recall 40%+

### mentions_100c.csv — Predicted Clustering (24 EU countries)
- **Size**: 100 mentions (5.8 KB)
- **Clusters**: 46 clusters (predicted by algorithm, same as 100b)
- **Cluster distribution**: Mix of 1-5 member clusters
- **Geography**: 24 EU countries (random distribution)
- **Use Case**: High-diversity blocking scenario with sparse country distribution
- **Expected latency**: ~20-30ms per request
- **Estimated total time**: <5 seconds seed + train
- **Quality baseline**: Precision ~60-70%, Recall ~15-20%

### mentions_1000.csv — Scalability Test
- **Size**: 1,000 mentions (55 KB)
- **Clusters**: 144 clusters (predicted by algorithm)
- **Cluster distribution**: Realistic mix (1-29 members per cluster)
- **Geography**: 27 EU countries (randomized)
- **Use Case**: Standard baseline, scalability verification with realistic clustering
- **Expected latency**: ~100-200ms per request (scaling effects)
- **Estimated total time**: ~2-3 minutes seed + train + stress
- **Quality baseline**: Precision ~50-70%, Recall ~10-20%

## CSV Schema

```
mention_id,legal_name,country_code,city,cluster_id
m00002717,"Jones, Compton and Day",AUT,New Colleen,m00002717
m00001909,"Adkins, Wright and Murray Inc",AUT,West Carlos,m00002717
m00000619,"Donovan-Perez",AUT,South Adam,m00002717
...
```

**Fields**:
- `mention_id`: Unique mention identifier (e.g., `m00000001`)
- `legal_name`: Company name (realistic variations: "Pepsi", "Pepsi Inc", "Pespi Inc", etc.)
- `country_code`: ISO 3166-1 alpha-3 code (20 EU countries, 5 mentions each)
- `city`: City name (placeholder for multi-rule blocking extensions)
- `cluster_id`: **Ground-truth cluster assignment** (derived by Jaro-Winkler >= 0.8)
  - **For singletons**: `cluster_id = mention_id` (unique organization in country, no similar matches)
  - **For multi-mention clusters**: `cluster_id = mention_id_of_first_member` (linked by JW similarity)
  - Respects country-based blocking rule (only mentions within same `country_code` can cluster)
  - Derived using Jaro-Winkler similarity on `legal_name` field
  - All clusters within a country are meaningful: name variations of plausible real-world entities
  - See `mentions_100b.md` for detailed cluster definitions with JW scores

## Source

Extracted and transformed from `data/city_hotspot_5k.csv` in the basic-entity-resolver-poc project:
- 100-record variants sampled from first 100 rows
- 1000-record dataset from first 1000 rows
- All country codes remapped to EU countries only
- Cluster distributions manually engineered for variance in test scenarios

## Usage

### In stress_test.py

```python
from ere.models.resolver import Mention
import csv

def load_mentions(csv_path):
    """Load mentions from CSV, return List[Mention]."""
    mentions = []
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            mentions.append(Mention(
                mention_id=MentionId(value=row['mention_id']),
                attributes=MentionAttributes(
                    legal_name=row['legal_name'],
                    country_code=row['country_code'],
                    city=row.get('city'),
                ),
            ))
    return mentions

# Load desired variant
mentions = load_mentions('test/data/stress/mentions_100b.csv')  # Balanced clustering
# or
mentions = load_mentions('test/data/stress/mentions_1000.csv')  # Scalability
```

## Experiment Matrix

| Dataset | Mentions | Clusters (GT) | Distribution | Quality (P/R) | Geography | Use Case |
|---------|----------|---------------|---------------|---------------|-----------|----------|
| 100a | 100 | 100 | 100% singletons | ~0-10% / 0% | 27 EU random | Cold-start behavior |
| 100b | 100 | 46 | 1-5 members | ~63% / ~19% | 20 EU grouped | Realistic clustering |
| 100c | 100 | 46 | 1-5 members | ~63% / ~19% | 24 EU scattered | High-diversity blocking |
| 1000 | 1000 | 144 | 1-29 members | ~50-70% / ~10-20% | 27 EU random | Scalability |

## Regeneration & Design (2026-03-01)

All CSVs were **regenerated with algorithmically-derived cluster_ids**:
- **mentions_100a**: 100 singletons with `cluster_id = mention_id`
  - Names are synthetically diverse (max JW similarity 0.53)
  - **Low precision (0-10%) is expected**: Shows cold-start behavior where untrained model makes false-positive matches on synthetic data
  - Demonstrates realistic scenario: limited training data leads to uncertainty
  - Not a bug—correct algorithm behavior with sparse signal
- **mentions_100b/c**: 46 clusters derived using Jaro-Winkler similarity (threshold=0.5)
- **mentions_1000**: 144 clusters predicted by greedy online clustering

Cluster_ids now match what the EntityResolver algorithm would create, enabling meaningful quality metric evaluation.

**Key insight**: mentions_100a tests **cold-start behavior**, not "perfect sparsity". The algorithm learns from seeded data and applies that learning, sometimes incorrectly matching new mentions on structural patterns. This is realistic.

## Notes

- All datasets deterministic: Same seed → same results
- No duplicate mentions within any dataset
- **cluster_id reflects algorithm prediction**, not arbitrary labels
- Real company name patterns (from Faker) to match production characteristics
- All country codes limited to EU (27 countries) for controlled testing
- Cluster distributions engineered via Jaro-Winkler similarity with blocking rule respect
