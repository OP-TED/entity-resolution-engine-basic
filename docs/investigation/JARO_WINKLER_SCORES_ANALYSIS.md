# Jaro-Winkler Scores Analysis: Understanding Low Similarity in ERE

**Date:** 2026-03-02
**Investigation:** Why m5 ("Acme Inc") gets low similarity scores (0.1718) when compared to m1 ("Acme Corp")

## Summary

The detailed trace logging revealed that Splink's output **does not include raw Jaro-Winkler scores**. Instead, it returns **gamma values** (comparison level indicators). By analyzing these gamma values, we determined the root cause of low similarity scores: **cold-start probability parameters are mistuned for this dataset**.

## Key Finding: Gamma Values Reveal Comparison Levels

Splink's dataframe columns include:
- `gamma_legal_name`: Comparison level (0, 1, or 2 for JaroWinkler at thresholds [0.9, 0.8])
- `gamma_country_code`: Comparison level (0 or 1 for ExactMatch)
- `match_probability`: Final probability output from Bayesian network
- `match_weight`: Log-odds from the model

### Gamma Level Interpretation

For `legal_name` field (JaroWinkler with thresholds [0.9, 0.8]):
- **Level 0** (gamma=0): Null level (not used for this comparison)
- **Level 1** (gamma=1): JW(legal_name_l, legal_name_r) is in range [0.8, 0.9)
- **Level 2** (gamma=2): JW(legal_name_l, legal_name_r) >= 0.9
- **Level 3, 4, ...**: Fallback/else levels (lower similarity)

For `country_code` field (ExactMatch):
- **Level 0** (gamma=0): No match
- **Level 1** (gamma=1): Exact match

## Observed Results

### High Similarity (Works Correctly)
**m1 "Acme Corp" vs m2 "Acme Corporation"** → **match_probability = 0.7941** ✓
- gamma_legal_name = 2 (JW >= 0.9, highest tier)
- gamma_country_code = 1 (exact match on US)
- **Result**: Strings are very similar, countries match → high confidence

### Low Similarity (Unexpected)
**m5 "Acme Inc" vs m1 "Acme Corp"** → **match_probability = 0.1718** ✗
- gamma_legal_name = 1 (JW in [0.8, 0.9))
- gamma_country_code = 1 (exact match on US)
- **Result**: Moderate name similarity, exact country match → LOW confidence (PROBLEM!)

### Very Low Similarity (Worst Case)
**m5 "Acme Inc" vs m2 "Acme Corporation"** → **match_probability = 0.0568** ✗✗
- gamma_legal_name = 0 (JW < 0.8, lowest tier)
- gamma_country_code = 1 (exact match on US)
- **Result**: Poor name similarity despite being more similar than m1

## Root Cause Analysis

### The Configuration Issue

Current cold-start parameters in `infra/config/resolver.yaml`:
```yaml
cold_start:
  comparisons:
    legal_name:
      m_probabilities: [0.80, 0.10, 0.10]  # [level1_JW>=0.9, level2_JW>=0.8, level3]
      u_probabilities: [0.02, 0.05, 0.93]
```

**The Problem**: The m_probability of **0.10** for level 1 (moderate JW match) is too low.

### How Splink's Bayesian Network Works

Splink uses m/u probabilities in a likelihood ratio model:
- **m_probability**: P(match level | records are a true match)
- **u_probability**: P(match level | records are NOT a match)

For level 1 (JW 0.8-0.9):
- m_prob = 0.10 means: "If records match, only 10% chance we'd see JW in [0.8, 0.9)"
- u_prob = 0.05 means: "If records don't match, 5% chance we'd see JW in [0.8, 0.9)"
- **Likelihood ratio**: 0.10 / 0.05 = 2.0 (barely above 1.0 = neutral!)

For comparison, level 2 (JW >= 0.9):
- m_prob = 0.80 means: "If records match, 80% chance we'd see JW >= 0.9"
- u_prob = 0.02 means: "If records don't match, 2% chance we'd see JW >= 0.9"
- **Likelihood ratio**: 0.80 / 0.02 = 40.0 (strong evidence of match!)

### Why m_prob=0.10 is Wrong

Under the assumption that moderate Jaro-Winkler similarity (0.8-0.9) is weak evidence of a match, the parameters make sense. **But for this dataset**, moderate similarity IS meaningful:

- "Acme Inc" and "Acme Corp" should arguably be related (both are company variants)
- The 0.8-0.9 JW range indicates partial string match
- With exact country match (US), the pair should score higher

The **cold-start parameters assume a prior distribution** that doesn't match the actual data distribution in this domain.

## Why "Acme Inc" vs "Acme Corporation" is < 0.8

This is a **Jaro-Winkler algorithm property**, not a bug:

```
"Acme Inc"       (8 chars)
"Acme Corporat" (16 chars)
```

Jaro-Winkler penalizes:
1. **Length mismatch**: 8 vs 16 is a big difference
2. **Transpositions**: None here, but matching window is small relative to length
3. **Match distance**: Characters must match within max(len(s1), len(s2))/2 - 1 positions

The result: JW("Acme Inc", "Acme Corporation") < 0.8

Meanwhile: JW("Acme Inc", "Acme Corp") is in [0.8, 0.9) because:
- Both are short (8 vs 9 chars)
- "Corp" is closer in length to "Inc" than "Corporation"

## Solutions

### Option 1: Adjust Cold-Start Parameters ⭐ RECOMMENDED
Increase m_probability for level 1 from 0.10 to 0.40-0.50:

```yaml
cold_start:
  comparisons:
    legal_name:
      m_probabilities: [0.80, 0.40, 0.10]  # Increased level 1 from 0.10
      u_probabilities: [0.02, 0.05, 0.93]  # Keep unchanged
```

**Effect**: Likelihood ratio for level 1 becomes 0.40 / 0.05 = 8.0 (much stronger signal)

### Option 2: Lower Match Weight Threshold
Change `match_weight_threshold` from -10 to 0.15-0.17 to accept lower-confidence matches:

```yaml
match_weight_threshold: 0.15
```

**Effect**: Pairs with match_probability >= 0.15 would be accepted

### Option 3: Train with EM
Provide real training data to Splink's EM algorithm instead of relying on cold-start defaults.

**Best for**: Production systems with sufficient labeled data

### Option 4: Accept Current Behavior
The current configuration treats moderate similarity as weak evidence, which is defensible for some use cases.

## Recommendation

**Option 1** is recommended because:
1. It's a parameter adjustment, not a threshold change
2. Empirically, moderate Jaro-Winkler matches (0.8-0.9) ARE meaningful for company names
3. It keeps the threshold logic intact (threshold = 0.5 for match_probability)
4. It aligns with domain knowledge: company name variants should group together

## Verification Steps

1. Update `infra/config/resolver.yaml` with m_prob=0.40 for level 1
2. Rebuild Docker image
3. Re-run demo
4. Verify: m5 "Acme Inc" should now join cluster with m1 "Acme Corp" (score > 0.5)

## References

- **Splink Documentation**: https://moj-analytical-services.github.io/splink/
- **Jaro-Winkler Algorithm**: https://en.wikipedia.org/wiki/Jaro%E2%80%93Winkler_distance
- **Bayesian Record Linkage**: Classic probabilistic matching using Fellegi-Sunter model
