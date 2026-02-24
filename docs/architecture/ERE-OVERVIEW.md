# Entity Resolution Engine (ERE) — Technical Overview

## What is ERE?

The **Entity Resolution Engine (ERE)** is an asynchronous service that resolves entity mentions to canonical clusters, enabling identification and linking of entities across documents. It operates as a pub/sub-based microservice consuming requests from the Entity Resolution System (ERS) client via Redis queues, performing resolution logic, and publishing responses with cluster assignments and confidence scores.

---

## Core Responsibilities

### 1. **Entity Mention Resolution**
**Primary use case:** Determine which existing cluster(s) an entity mention belongs to.

```
Client Request                    ERE Processing                  Response
───────────────────────────────  ────────────────────────────── ──────────────
EntityMentionResolutionRequest   ✓ Validate request             EntityMentionResolutionResponse
├─ EntityMention                 ✓ Find nearest clusters         ├─ entityMentionId
│  ├─ requestId (URI)            ✓ Calculate similarity scores   ├─ candidates (list)
│  ├─ sourceId                   ✓ Apply threshold logic         │  ├─ clusterId (URI)
│  ├─ entityType (e.g., Org)     ✓ Assign or create cluster      │  └─ confidenceScore (0.0–1.0)
│  └─ content (RDF/XML/JSON)     ✓ Update cluster centroids      └─ timestamp
├─ ereRequestId                  ✓ Store audit trail
└─ timestamp
```

### 2. **Cluster Lifecycle Management**
**Scenarios:**

| Scenario | Action | Result |
|----------|--------|--------|
| **Known entity** | Entity mention matches existing cluster (distance < threshold) | Entity assigned to best-matching cluster(s); confidence score reflects similarity |
| **New entity** | No close matches found (distance ≥ threshold) | New singleton cluster created; entity becomes canonical member (confidence = 1.0) |
| **Ambiguous entity** | Multiple candidate clusters at similar distances | All candidates returned; client curates or engine applies conflict resolution |

### 3. **Cluster Curation & Re-evaluation**
**Secondary workflow:** Curator feedback loop allows authoritative re-assessment of provisional cluster assignments.

```
Provisional State              Curator Action           Final State
─────────────────────────────  ──────────────────────── ──────────────
Entity → Cluster A (score 0.75) Disagree, move to B → Entity → Cluster B (authoritative)
                                Accept (no change)   → Entity → Cluster A (verified)
                                Split into 2 clusters → Entity → New Cluster C
```

### 4. **Read-Only Canonical Lookup**
**Lightweight operation:** Query the canonical cluster for an entity without initiating resolution.

```
CanonicalLookupRequest(entityUri)
  → Immediate response: ClusterReference (no async, no time budget)
```

---

## Request/Response Contract

### EntityMentionResolutionRequest (Normative)

**Structure:**
```python
@dataclass
class EntityMentionResolutionRequest(ERERequest):
    entityMention: EntityMention          # The mention to resolve
    ereRequestId: str                     # Unique request identifier
    timestamp: str (ISO 8601)             # Request timestamp

@dataclass
class EntityMention:
    identifier: EntityMentionIdentifier   # Unique ID + type + source
    contentType: str                      # Format: "text/turtle", "application/json", etc.
    content: str                          # Serialized entity data (RDF, JSON, XML)

@dataclass
class EntityMentionIdentifier:
    requestId: str                        # URI of the entity mention
    sourceId: str                         # Source system identifier
    entityType: str                       # URI of entity type (e.g., http://www.w3.org/ns/org#Organization)
```

### EntityMentionResolutionResponse (Normative)

**Structure:**
```python
@dataclass
class EntityMentionResolutionResponse(EREResponse):
    ereRequestId: str                     # Echo of request ID
    entityMentionId: EntityMentionIdentifier # Source entity
    candidates: list[ClusterReference]    # Candidate clusters (sorted by confidence)
    timestamp: str (ISO 8601)             # Response timestamp

@dataclass
class ClusterReference:
    clusterId: str                        # URI of the cluster
    confidenceScore: float (0.0–1.0)      # Confidence in the match
```

### Error Responses

**On failure (invalid entity type, malformed input, resolver failure):**
```python
@dataclass
class EREErrorResponse(EREResponse):
    ereRequestId: str
    errorTitle: str                       # Short error summary
    errorDetail: str                      # Detailed error message
    errorType: str                        # Fully qualified exception type
    timestamp: str (ISO 8601)
```

---

## Asynchronous Interaction Pattern

### Pub/Sub Exchange (Normative)

```
ERS Client                  Redis Channels              ERE Service
──────────────────────────  ──────────────────────────  ────────────────────
1. Publish request       → [ere:requests]           → 1. Consume request
   (EntityMentionResolution                            2. Validate
    Request)
                                                       3. Query cluster DB
                                                       4. Apply resolution logic
                                                       5. Store assignment
                                                       6. Publish response
                         ← [ere:responses]          ← 7. EntityMentionResolution
2. Consume response         (EntityMentionResolution     Response
   (latest outcome)         Response)
3. Store mapping
   (entity → cluster)
```

**Guarantees:**
- **Asynchronous:** Request and response are decoupled; no blocking waits
- **Idempotent:** Resending the same request (same `ereRequestId`) returns the same response (latest outcome)
- **Latest-outcome semantics:** If multiple responses exist for a request ID, only the latest is guaranteed
- **No guaranteed ordering:** Responses may arrive out of order; client must handle via `ereRequestId` matching

---

## Architecture Layers (Cosmic Python)

```
┌──────────────────────────────────────────┐
│ Entrypoints                              │
│  ├─ Redis service (pub/sub consumer)     │
│  └─ Direct client API (mock/testing)     │
└──────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────┐
│ Services (Use Cases)                     │
│  ├─ AbstractPubSubResolutionService      │
│  │  └─ Orchestrates resolution workflow  │
│  └─ Resolution logic coordination        │
└──────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────┐
│ Models (Domain)                          │
│  ├─ EntityMentionResolutionRequest       │
│  ├─ EntityMentionResolutionResponse      │
│  ├─ Cluster, ClusterReference            │
│  └─ Business rules (distance, threshold) │
└──────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────┐
│ Adapters (Infrastructure)                │
│  ├─ AbstractResolver (pluggable strategy)│
│  ├─ Redis adapter (pub/sub)              │
│  ├─ Database adapter (cluster store)     │
│  └─ RDF/entity data deserializer         │
└──────────────────────────────────────────┘
```

---

## Key Design Patterns

### 1. **Strategy Pattern (Resolver)**
Multiple resolution strategies can be plugged in without changing the service:
- `MockResolver` — Test data for development
- `BasicResolver` — Simple string matching or RDF analysis
- Future: ML-based, domain-specific resolvers

### 2. **Template Method (PubSubResolutionService)**
Abstract service defines the workflow; concrete implementations handle transport:
- `RedisResolutionService` — Production Redis pub/sub
- `MockPubSubService` — In-memory queues for testing

### 3. **Repository Pattern**
Cluster store abstraction allows multiple backends:
- In-memory (test)
- RDF graph (current)
- Relational database (future)

### 4. **Separation of Concerns**
- **Services** handle orchestration, not I/O
- **Adapters** handle external systems (Redis, DB, RDF)
- **Models** contain pure domain logic, no framework dependencies

---

## Time Budgets & Provisional States

ERE supports two time budgets for resolution requests:

| Budget | Purpose | Action |
|--------|---------|--------|
| **Hard timeout** | Prevent indefinite blocking | Service must respond within deadline (e.g., 5s) |
| **Soft timeout** | Provisional assignments | Within soft window, attempt higher-confidence matches; after, respond with current best |

**Example:**
```
Request arrives at t=0
├─ t=0-100ms: Quick lookup finds candidate (confidence 0.8)
├─ t=100-500ms: Soft timeout expires → respond with 0.8 candidate if no better match
├─ t=500-1000ms: Hard timeout → must respond (response with 0.8 or error)
```

---

## Integration Points

### With ERS (Entity Resolution System)
- **Consumer:** Listens to ERS publication of `EntityMentionResolutionRequest`
- **Producer:** Publishes `EntityMentionResolutionResponse` back to ERS
- **Channel:** Redis pub/sub (configurable)

### With Data Sources
- **Input:** Entity mention data (RDF, JSON, XML)
- **Output:** Cluster assignments + confidence scores

### With Curator
- **Feedback loop:** Curator accepts/rejects/refines provisional assignments
- **Re-evaluation:** Updates cluster state based on authoritative feedback

---

## Testing & Validation

### Unit Test Coverage (80%+ target)
- **Models:** Domain invariants, validation rules
- **Services:** Resolution workflow, edge cases (threshold boundary, new cluster creation)
- **Adapters:** Mock + real resolver behavior

### BDD Features
- Entity mention resolution scenarios (known, unknown, malformed)
- Cluster assignment workflows
- Error handling

### Integration Tests
- Full resolution cycle with mock resolver + in-memory queues
- Redis pub/sub exchange
- Idempotency guarantees

---

## Quality & Maintainability

### SOLID Principles Enforced
- **SRP:** Resolver, service, client, adapter each have one reason to change
- **OCP:** New resolver strategies can be added without modifying service
- **LSP:** All resolvers respect the `AbstractResolver` contract
- **ISP:** Clients depend only on the methods they use
- **DIP:** Service depends on `AbstractResolver` abstraction, not concrete implementation

### Architecture Contracts
- Layer dependencies via `import-linter` (entrypoints → services → models + adapters)
- No circular imports; top-level policy independent of infrastructure details
- Models contain no framework or I/O dependencies

### Code Quality Gates
- Pylint: SOLID principle violations flagged
- Coverage: 80% minimum on new code
- Complexity: Cyclomatic max 10, maintainability index min B
- SonarCloud: Quality gates on critical issues, blockers, duplicates

---

## Related Documents

- **Sequence Diagrams:** `/docs/architecture/sequence_diagrams/` — Normative interaction flows
- **Breadboards:** `/docs/breadboards.md` — Component structure (services, clients, resolvers)
- **Resolution Tools:** `/docs/resolution-tools.md` — Resolver implementation options
- **CLAUDE.md:** Project coding standards (Clean Architecture, SOLID, testing strategy)

---

## Glossary

| Term | Definition |
|------|-----------|
| **Entity Mention** | A reference to an entity appearing in a document (e.g., "Acme Inc.") |
| **Cluster** | A canonical group of entity mentions resolved to the same real-world entity |
| **Confidence Score** | 0.0–1.0 measure of similarity between a mention and cluster candidate |
| **Threshold** | Distance/similarity cutoff; mentions below threshold create new clusters |
| **Canonical Member** | The authoritative representative of a cluster (usually confidence = 1.0) |
| **Provisional** | Tentative assignment pending curator review or hard timeout |
| **Resolver** | Pluggable strategy for computing similarity between entity mention and clusters |
| **Pub/Sub** | Publisher/subscriber messaging pattern (Redis, message queues) |

