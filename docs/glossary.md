# Business Glossary

This document defines the domain terms and business rules for the Entity Resolver component.

---

## Terms

| Term | Definition |
|---|---|
| **Mention** | An incoming data record representing one observation of a real-world entity. The primary unit processed in each resolution request. A mention belongs to exactly one cluster at any point in time. |
| **Entity** | A distinct real-world organization that one or more mentions may refer to. Not directly stored — inferred through the cluster a mention belongs to. |
| **Entity Resolution** | The process of determining which mentions refer to the same real-world entity and grouping them accordingly. |
| **Cluster** | A set of mentions determined to refer to the same real-world entity. Each cluster has a unique ID, initialized to the mention ID of the first mention in the cluster. |
| **Cluster ID** | The identifier of a cluster. Initialized to the mention ID of the first mention assigned to that cluster. Serves as the canonical identifier for the entity the cluster represents. |
| **Cluster Reference** | A `(cluster_id, score)` pair returned as part of the resolution output. Identifies a candidate cluster and expresses how strongly it is associated with the resolved mention. |
| **Resolution Request `r(m)`** | A request to resolve a single mention `m`. Produces a ranked list of cluster references, with the top-ranked entry being the algorithm's implied canonical cluster for the mention. |
| **Blocking** | A pre-filtering step that narrows the set of existing mentions to compare against, based on blocking rules. Reduces unnecessary computation. |
| **Blocking Rules (BR)** | Declarative rules used to eliminate mention pairs that cannot plausibly match (e.g., different country). |
| **Pairwise Similarity Score** | A numeric value in [0, 1] expressing how similar two mentions are, as computed by the similarity function. |
| **Threshold (THR)** | The minimum pairwise similarity score required for a mention to be added to an existing cluster. Default: 0.8. |
| **Mention Link** | A recorded association between two mentions for which a similarity score has been computed, regardless of whether that score meets THR. Used for candidate cluster discovery. |
| **Cluster Extension** | The act of adding a mention to an existing cluster because its best pairwise similarity with any existing mention is ≥ THR. A mention can be added to at most one cluster per resolution request. |
| **Comparison Function / Identity Function** | A per-entity-type function that defines which entity properties are taken into consideration when determining similarity between two mentions. Fixed per entity type. |
| **Candidate Clusters / Cluster References** | The output of a resolution request: a ranked list of cluster references, pruned to top-N. Cannot be empty. The top entry is the implied canonical cluster for the resolved mention. |
| **N** | The maximum number of cluster references returned per resolution request. Default: 100. User-configurable. |

---

## Business Rules

1. Each resolution request processes exactly one mention and always returns at least one cluster reference.
2. The top-ranked cluster reference in the output is the algorithm's implied canonical cluster for the mention.
3. A mention is added to an existing cluster only if its best pairwise similarity with any existing mention is ≥ THR.
4. Only the single best-matching existing mention determines cluster assignment per request.
5. If no candidate passes THR (or blocking produces an empty candidate set), a new singleton cluster is created with Cluster ID = mention ID.
6. All computed pairwise similarities are stored — including those below THR — as mention links.
7. Candidate cluster discovery (`genCand`) uses mention links regardless of THR, then ranks by cluster-level similarity score.
8. Output is always pruned to top-N cluster references.
9. A mention belongs to exactly one cluster at any point in time.
10. No global reclustering: cluster state is updated incrementally per resolution request.
11. Comparison Function is fixed per entity type.
12. Data management must be efficient: computations that can be performed at the database level must be done there; excessive data fetching into application memory must be avoided.
