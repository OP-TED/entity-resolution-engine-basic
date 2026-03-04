# Entity Resolution Algorithm

## Overview

The ERE (Entity Resolution Engine) implements an **online clustering algorithm** that resolves entity mentions into clusters incrementally as they arrive. Each incoming mention is scored against existing mentions, assigned to the best-matching cluster (if the similarity meets a threshold), or creates a new singleton cluster.



## Core Concept

Mentions are grouped into **clusters** representing the same real-world entity. A mention belongs to exactly one cluster at any given time. When a new mention arrives:

1. **Score** it against existing mentions using a similarity function and evaluate match probablity
2. **Persist** all computed match probablities (mention-links)
3. **Assign** the mention to the best-matching cluster or create a new one
4. **Return** a ranked list of candidate clusters



## Resolution Flow

For each incoming mention `m`:

### Step 0: Check for Known Mention (Idempotency)
If the mention was already resolved in a prior request:
- **Return cached result** (the ranked list of candidates from the previous resolution)
- Do not re-run the full resolution pipeline (avoids duplicate entries in repositories)
- The cached result reflects current cluster state (if other mentions have joined the cluster since, scores may have updated)

If the mention is unknown, proceed to Step 1.

### Step 1: Find Candidates
Apply **blocking rules** to identify a subset of existing mentions to compare with (reduces computational cost). This prevents every new mention from being compared against every existing mention.

### Step 2: Compute Similarities
Compare the new mention against all candidate mentions using a similarity linker (e.g., Splink for probabilistic name matching). This produces:
- **Pairwise similarity scores** (all stored, regardless of threshold)
- **Mention-links**: records that a comparison exists between two mentions

Note: The algorithm delegates similarity computation to Splink, which provides match probabilities. These roughly correspond to similarity scores but differ in one significant aspect: Splink probabilities are discrete (not continuous) for performance reasons. Consequently, two pairs of mentions may have slightly different similarity scores (e.g., Jaro-Winkler) but the same probability score. Nevertheless, this has no major impact on the overall outcome.

### Step 3: Cluster Assignment (Greedy Online)
- Find the **best-matching mention** (highest similarity among candidates)
- If best similarity ≥ **threshold**:
  - **Extend** the cluster of the best match
- Otherwise:
  - **Create new singleton cluster** with this mention as the sole member. Similarity to the new cluster is 0.

Note: Order of arrival matters. The algorithm makes a greedy decision based only on the best current match, with no retrospective re-clustering.

### Step 4: Persist and Update
- Save the mention to the repository (now part of the search space)
- Register the mention with the similarity linker (part of the candidate set for future mentions)

### Step 5: Generate Candidate Output
Return a ranked list of candidate clusters:
- Include the cluster the mention was assigned to (with best-match similarity, or 0.0 if singleton)
- Include other clusters that have a computed link to this mention (below-threshold similarities)
- Rank by similarity score
- Prune to top-N (configurable, default 100)

### Step 5: Generate Candidate Output
Return a ranked list of candidate clusters:
- Include the cluster to which the mention was assigned (with best-match similarity, or 0.0 if singleton)
- Include other clusters that have a computed link to this mention (below-threshold similarities)
- Rank by similarity score
- Prune to top-N (configurable, default 100)

Output is never empty; at least the cluster to which the mention was assigned (existing or newly created) is always returned.



## Key Design Decisions

### All Similarities Stored, Not All Create Edges
- **Mention-links** (computed similarities) are preserved regardless of threshold; they're used to propose alternative candidate clusters in the resolution response
- **Cluster membership** (cluster edges) uses only the single best match ≥ threshold
- This enables:
  - Cluster formation via strong matches only
  - Alternative candidates to be returned even if below threshold (for user review, A/B testing, etc.)

### Threshold vs. Below-Threshold
- **Threshold-gated**: Determines whether a mention joins an existing cluster
- **Below-threshold links**: Still recorded; contribute to candidate generation and ranking
- A mention can appear as a candidate for multiple clusters via different link paths

### Online Greedy, Not Batch
The algorithm processes mentions one at a time, making immediate clustering decisions. This is efficient but order-dependent:
- Early mentions establish clusters
- Later mentions join based on similarity to whoever was seen first
- Retrospective re-clustering is not performed



## Configuration Parameters

| Parameter | Purpose |
|--||
| **threshold** | Minimum similarity score to extend an existing cluster |
| **top_n** | Maximum candidate clusters returned per mention |
| **blocking_rules** | Pre-filters to reduce similarity computation |



## Outputs

For each resolved mention, the service returns a **ResolutionResult**:

```python
ResolutionResult(
    candidates: tuple[
        CandidateCluster(
            cluster_id: ClusterId,  # Unique cluster identifier
            score: float            # Similarity score (best mention-link to this cluster)
        ),
        ...
    ]
)
```

**Properties:**
- **Non-empty**: Always contains at least one candidate (the mention's own cluster)
- **Ranked**: Sorted descending by score
- **Pruned**: Limited to top-N candidates (default 100, configurable)
- **Complete**: Includes:
  - The cluster the mention was assigned to (score = 0.0 if singleton, or best-match similarity)
  - Other clusters linked via mention-links (below-threshold similarities)

The first CandidateCluster (`.candidates[0]`) is the algorithm's implied best cluster for the mention. Additional references represent alternatives based on computed similarities.
