# ERE Cosmic Python Architecture

**Entity Resolution Engine (ERE) — Layered Architecture Blueprint**

Following [Meaningfy Clean Code Standards](../../CLAUDE.md) and [Cosmic Python](../CLAUDE.md) patterns, this document describes the four-layer architecture of the Entity Resolution Engine and its integration with the Entity Resolution System (ERS).

---

## Executive Summary

The ERE is a **microservice orchestrator** that:

1. **Consumes async requests** from ERS via Redis pub/sub (`EntityMentionResolutionRequest`)
2. **Resolves entity mentions** against a cluster knowledge base
3. **Produces responses** with cluster candidates and confidence scores
4. **Manages cluster lifecycle** (match to existing, create new, update centroids)

**Design principle:** Strict layered separation following **Cosmic Python**, with dependency flow:
```
entrypoints → services → (adapters + models)
```

This ensures that:
- ✅ Domain logic (`models`) is testable without I/O
- ✅ Infrastructure (`adapters`) is replaceable
- ✅ Orchestration (`services`) is business-focused
- ✅ Requests (`entrypoints`) are thin and focused

---

## Architecture Layers

### Layer 1: Models (Domain Logic)

**Responsibility:** Pure domain entities, value objects, and business rules. **No I/O, no frameworks.**

**Key Classes:**

| Class | Purpose | Notes |
|-------|---------|-------|
| `EntityMention` | Represents a reference to an entity in a document | Identifier (requestId, sourceId, entityType) + content + contentType |
| `EntityMentionIdentifier` | Unique entity mention identity | Composed: requestId (URI), sourceId, entityType (URI) |
| `Cluster` | Canonical group of resolved entity mentions | clusterId, members, centroid (aggregate properties) |
| `ClusterReference` | Response reference to a cluster | clusterId + confidenceScore (0.0–1.0) |
| `ResolutionRequest` | Standardized input contract | EntityMentionResolutionRequest wrapper |
| `ResolutionResponse` | Standardized output contract | EntityMentionResolutionResponse wrapper |
| `ThresholdDecision` | Distance-based assignment logic | "distance < threshold → match; else → new cluster" |

**Location:** `src/ere/models/`

**Key Business Rules (unit-testable):**

```python
# Example: threshold-based cluster assignment logic
def should_match_cluster(distance: float, threshold: float) -> bool:
    """Pure logic: no I/O, no adapters."""
    return distance < threshold

def calculate_confidence(distance: float, max_distance: float) -> float:
    """Transform distance (0..max) into confidence (1.0..0.0)."""
    if distance >= max_distance:
        return 0.0
    return 1.0 - (distance / max_distance)
```

**Testing Strategy for Models:**

- ✅ Unit tests focus on **domain invariants** (what makes a valid cluster, mention, score)
- ✅ No mocking; fast, deterministic, isolated
- ✅ Test edge cases (boundary distances, confidence at 0.0 and 1.0, empty clusters)
- ✅ Target: 90%+ coverage, <5 lines per test case

**Example test:**
```python
def test_confidence_score_at_distance_threshold():
    assert calculate_confidence(distance=0.5, max_distance=1.0) == 0.5
    assert calculate_confidence(distance=0.0, max_distance=1.0) == 1.0
    assert calculate_confidence(distance=1.0, max_distance=1.0) == 0.0
```

---

### Layer 2: Adapters (Infrastructure & Integration)

**Responsibility:** External systems (database, Redis, resolvers, file stores). Implement repositories and gateways.

**Dependency rule:** Depends on `models` **only**. Never on `services` or `entrypoints`.

**Key Adapters:**

| Adapter | Purpose | External System |
|---------|---------|-----------------|
| `AbstractResolver` | Strategy interface for similarity computation | Pluggable: mock, basic string matching, ML-based |
| `MockResolver` | Test double (in-memory, deterministic) | N/A (test only) |
| `BasicResolver` | Simple string similarity (Levenshtein, RDF analysis) | In-process |
| `ClusterRepository` | Persist & retrieve clusters | Graph DB (RDF) or relational DB |
| `RedisAdapter` | Pub/sub message consumer/producer | Redis queues |
| `EntityDeserializer` | Parse entity content (RDF/XML/JSON) | Serialization format handlers |

**Location:** `src/ere/adapters/`

**Dependency Inversion (DIP) Example:**

```python
# Abstract interface — models-level contract
class AbstractResolver(ABC):
    @abstractmethod
    def find_clusters(self, mention: EntityMention) -> list[ClusterCandidate]:
        """Returns candidates ranked by similarity. No I/O details here."""
        pass

# Concrete implementation — adapters-level detail
class BasicResolver(AbstractResolver):
    def __init__(self, cluster_repo: ClusterRepository):
        self.cluster_repo = cluster_repo  # Injected dependency

    def find_clusters(self, mention: EntityMention) -> list[ClusterCandidate]:
        clusters = self.cluster_repo.find_all()  # I/O happens here
        candidates = [
            ClusterCandidate(cluster=c, distance=self._compute_distance(mention, c))
            for c in clusters
        ]
        return sorted(candidates, key=lambda x: x.distance)
```

**Services never import `BasicResolver` directly:**
```python
# ✅ Correct: services depend on abstraction
class ResolutionService:
    def __init__(self, resolver: AbstractResolver):  # DIP: inject abstraction
        self.resolver = resolver
```

**Testing Strategy for Adapters:**

- ✅ Unit tests verify **integration contracts** (can we call the resolver? does it return valid responses?)
- ✅ Use mocks for external systems (mock Redis, in-memory cluster DB)
- ✅ Adapters are **double-checked**: test both the adapter AND the external system separately
- ✅ Target: 80%+ coverage on integration points
- ✅ Keep tests isolated; one adapter per test file

**Example test:**
```python
def test_resolver_returns_sorted_candidates():
    """Mocked resolver should return candidates sorted by distance."""
    mock_repo = MockClusterRepository(clusters=[...])
    resolver = BasicResolver(cluster_repo=mock_repo)

    mention = EntityMention(identifier=..., content="Acme Inc.")
    candidates = resolver.find_clusters(mention)

    assert candidates[0].distance <= candidates[1].distance  # Sorted
    assert all(isinstance(c, ClusterCandidate) for c in candidates)
```

---

### Layer 3: Services (Use-Case Orchestration)

**Responsibility:** Business workflows, transaction boundaries, orchestration of models and adapters.

**Dependency rule:** Depends on `models` and `adapters`. Never on `entrypoints`.

**Core Services:**

| Service | Purpose |
|---------|---------|
| `AbstractPubSubResolutionService` | Abstract template for pub/sub workflow |
| `RedisResolutionService` | Production pub/sub (async request/response) |
| `DirectResolutionService` | Synchronous (for testing, direct API) |
| `ResolutionOrchestrator` | High-level use-case coordination |

**Location:** `src/ere/services/`

**Key Workflow (from `AbstractPubSubResolutionService`):**

```python
class AbstractPubSubResolutionService(ABC):
    def __init__(self, resolver: AbstractResolver, repo: ClusterRepository):
        self.resolver = resolver
        self.repo = repo

    def resolve_entity_mention(self, request: ResolutionRequest) -> ResolutionResponse:
        """
        Template method: orchestrates models + adapters for one request.
        Subclasses override transport (Redis, direct, etc.), not logic.
        """
        # 1. Validate request
        self._validate_request(request)

        # 2. Find nearest clusters
        candidates = self.resolver.find_clusters(request.mention)

        # 3. Apply business rules (threshold logic from models)
        best_candidate = self._select_best_candidate(candidates)

        # 4. Persist decision
        if best_candidate and best_candidate.distance < THRESHOLD:
            self.repo.assign_mention_to_cluster(
                request.mention, best_candidate.cluster_id
            )
            self.repo.update_cluster_centroid(best_candidate.cluster_id)
        else:
            new_cluster = self.repo.create_new_cluster(request.mention)
            best_candidate = ClusterCandidate(new_cluster, confidence=1.0)

        # 5. Return response
        return ResolutionResponse(
            ereRequestId=request.ereRequestId,
            entityMentionId=request.mention.identifier,
            candidates=[best_candidate],
            timestamp=now_iso8601()
        )

    @abstractmethod
    def start_consuming(self):
        """Subclasses implement pub/sub transport."""
        pass
```

**Subclass Example (Redis pub/sub):**

```python
class RedisResolutionService(AbstractPubSubResolutionService):
    def __init__(self, resolver: AbstractResolver, repo: ClusterRepository, redis_client):
        super().__init__(resolver, repo)
        self.redis_client = redis_client

    def start_consuming(self):
        """Listen on Redis channel."""
        pubsub = self.redis_client.pubsub()
        pubsub.subscribe("ere:requests")

        for message in pubsub.listen():
            if message["type"] == "message":
                request = json.loads(message["data"])
                response = self.resolve_entity_mention(request)
                self.redis_client.publish("ere:responses", json.dumps(response))
```

**Transaction Boundaries:**

- Each `resolve_entity_mention()` call is **one unit of work**
- Database operations are grouped: validate → query → decide → persist
- Errors are caught at service level; partial updates are rolled back

**Testing Strategy for Services:**

- ✅ Unit tests verify **orchestration logic** (request → validation → decision → response)
- ✅ Use mocks for adapters (mock resolver, mock repo)
- ✅ Test both happy path and edge cases (no clusters, threshold boundary, error handling)
- ✅ Target: 85%+ coverage (high risk area)
- ✅ Use parametrization for multiple scenarios

**Example test:**
```python
def test_resolution_creates_new_cluster_when_no_match():
    """When all candidates exceed threshold, create new cluster."""
    mock_resolver = MockResolver(candidates=[])  # No matches
    mock_repo = MockClusterRepository()
    service = ResolutionService(resolver=mock_resolver, repo=mock_repo)

    request = ResolutionRequest(mention=EntityMention(...), ereRequestId="123")
    response = service.resolve_entity_mention(request)

    assert len(response.candidates) == 1
    assert response.candidates[0].confidenceScore == 1.0  # New singleton
    assert mock_repo.new_cluster_created  # Verify persistence
```

---

### Layer 4: Entrypoints (Request/Response Boundaries)

**Responsibility:** Parse external input, call services, format responses. Minimal business logic.

**Dependency rule:** Depends on `services` (and indirectly on `models` and `adapters`).

**Entrypoints:**

| Entrypoint | Protocol | Role |
|------------|----------|------|
| `RedisConsumer` | Redis pub/sub | Async: consume requests, publish responses |
| `DirectAPIClient` | Direct method calls | Testing, mock use cases |
| `HealthCheck` | HTTP (if exposed) | Liveness/readiness for orchestration |

**Location:** `src/ere/entrypoints/`

**Example Implementation:**

```python
class RedisConsumer:
    """Primary entrypoint: Redis pub/sub consumer."""

    def __init__(self, service: RedisResolutionService, config: Config):
        self.service = service
        self.config = config

    def run(self):
        """Start listening on Redis channel."""
        self.service.start_consuming()  # Delegates to service

class DirectAPIClient:
    """Test/mock entrypoint: direct method calls."""

    def __init__(self, service: AbstractPubSubResolutionService):
        self.service = service

    def resolve(self, entity_mention: dict) -> dict:
        """Synchronous wrapper for testing."""
        try:
            request = ResolutionRequest.from_dict(entity_mention)
            response = self.service.resolve_entity_mention(request)
            return response.to_dict()
        except ValidationError as e:
            return {"error": str(e), "type": "ValidationError"}
```

**Error Handling:**

- Entrypoints catch framework-level errors (Redis connection loss, JSON parse errors)
- Errors are logged and wrapped in standard error responses
- Services propagate domain-level errors; entrypoints translate them

**Testing Strategy for Entrypoints:**

- ✅ Unit tests verify **request/response contracts** (can we parse JSON? do we return valid HTTP status?)
- ✅ Mock the service; focus on parsing, routing, error wrapping
- ✅ Test edge cases (malformed JSON, missing fields, network timeouts)
- ✅ Target: 80%+ coverage

**Example test:**
```python
def test_redis_consumer_publishes_response_on_valid_request():
    """Verify request → service → response → publish flow."""
    mock_service = MockResolutionService(...)
    mock_redis = MockRedis()
    consumer = RedisConsumer(service=mock_service, redis_client=mock_redis)

    # Simulate Redis message
    mock_redis.publish("ere:requests", json.dumps({
        "entityMention": {...},
        "ereRequestId": "123"
    }))

    consumer.run()  # Process one message

    # Verify response was published
    assert mock_redis.published_to("ere:responses")
```

---

## Dependency Diagram

```
┌────────────────────────────────────────────┐
│ Entrypoints                                │
│  ├─ RedisConsumer (pub/sub listener)       │
│  └─ DirectAPIClient (mock/testing)         │
└────────────────────────────────────────────┘
                    ↓
┌────────────────────────────────────────────┐
│ Services                                   │
│  ├─ AbstractPubSubResolutionService        │
│  │   ├─ resolve_entity_mention()           │
│  │   ├─ _validate_request()                │
│  │   └─ _select_best_candidate()           │
│  ├─ RedisResolutionService                 │
│  └─ DirectResolutionService                │
└────────────────────────────────────────────┘
              ↙        ↘
      ┌──────────┐   ┌──────────────────┐
      │ Models   │   │ Adapters         │
      │ ─────────│   │ ─────────────────│
      │ - Entity │   │ - AbstractResolver
      │Mention   │   │ - ClusterRepo    │
      │ - Cluster│   │ - RedisAdapter   │
      │Reference │   │ - Deserializer   │
      │ - Rules  │   │ ↓ (depends on)   │
      │          │   │ Models ↑         │
      └──────────┘   └──────────────────┘
```

---

## SOLID Principles Enforcement

### 1. **SRP — Single Responsibility Principle**

✅ **Models** have one reason to change: domain rules evolve
✅ **Adapters** have one reason to change: external system contracts change
✅ **Services** have one reason to change: business workflows change
✅ **Entrypoints** have one reason to change: input/output protocols change

**Example SRP violation (caught by pylint):**
```python
# ❌ Bad: service does I/O + business logic
class ResolutionService:
    def resolve(self, mention_dict):
        redis_client.hset(...)  # I/O in service!
        # Should be in adapters
```

**Enforcement:**
- `pylint` limits functions to ≤50 lines (SRP → smaller units)
- `import-linter` blocks service imports into models
- Code review: "What reasons to change does this class have?"

### 2. **OCP — Open/Closed Principle**

✅ New resolver strategies extend `AbstractResolver` without modifying existing code
✅ New pub/sub transports extend `AbstractPubSubResolutionService` without modifying core logic

**Example OCP (extensible):**
```python
# ✅ New resolver: just extend the interface
class MLResolver(AbstractResolver):
    def find_clusters(self, mention: EntityMention) -> list[ClusterCandidate]:
        # ML-based similarity
        pass

# Service works with any resolver
service = ResolutionService(resolver=MLResolver(...))
```

**Enforcement:**
- `import-linter` ensures new adapters don't reverse dependencies
- Architecture reviews: "Can we add a new resolver without changing services?"

### 3. **LSP — Liskov Substitution Principle**

✅ All resolvers (`MockResolver`, `BasicResolver`, `MLResolver`) are substitutable
✅ All repository implementations conform to `ClusterRepository` contract

**Example LSP (all compatible):**
```python
# All of these work with the same service
service = ResolutionService(resolver=MockResolver(...))
service = ResolutionService(resolver=BasicResolver(...))
service = ResolutionService(resolver=MLResolver(...))
```

**Enforcement:**
- Abstract base classes define contracts (ABC + @abstractmethod)
- Tests verify each subclass respects the contract

### 4. **ISP — Interface Segregation Principle**

✅ Adapters only depend on methods they use (no "fat" interfaces)
✅ Services only call methods they need from adapters

**Example ISP:**
```python
# ✅ Minimal interface
class ClusterRepository:
    def find_by_id(self, id: str) -> Cluster: pass
    def create(self, cluster: Cluster) -> Cluster: pass

# Services don't need (and don't call) unrelated methods
# e.g., no delete() in core workflow
```

### 5. **DIP — Dependency Inversion Principle**

✅ Services depend on `AbstractResolver`, not concrete `BasicResolver`
✅ Resolvers injected via constructor (not imported)
✅ High-level policy (services) never depends on low-level details (adapters)

**Example DIP:**
```python
# ✅ Correct: inject abstraction
class ResolutionService:
    def __init__(self, resolver: AbstractResolver):
        self.resolver = resolver

# ❌ Wrong: direct import of concrete class
class ResolutionService:
    def __init__(self):
        self.resolver = BasicResolver()  # Violates DIP
```

**Enforcement:**
- `import-linter` blocks direct imports of adapters in services
- Dependency injection container wires everything at app startup

---

## Testing Strategy (per layer)

| Layer | Focus | Example Test | Tool | Coverage |
|-------|-------|--------------|------|----------|
| **Models** | Domain rules, invariants | `test_confidence_at_threshold()` | pytest | 90%+ |
| **Adapters** | I/O contracts, mocks | `test_resolver_returns_sorted()` | pytest + mock | 80%+ |
| **Services** | Orchestration, workflows | `test_creates_cluster_on_no_match()` | pytest + mock | 85%+ |
| **Entrypoints** | Request/response parsing | `test_publishes_response()` | pytest + mock | 80%+ |
| **End-to-end** | Full resolution cycle | `test_entity_mention_resolution` | pytest-bdd | 1–2 scenarios |

### BDD Features (Gherkin)

Business-readable scenarios:

```gherkin
Feature: Entity Mention Resolution
  Scenario Outline: Resolving known entities
    Given an ERE service with populated clusters
    When I submit a resolution request for entity "<entity>"
    Then I receive a response with "<num_candidates>" candidate clusters

    Examples:
      | entity | num_candidates |
      | entity-001 | 1 |
      | entity-002 | 3 |

  Scenario: Creating a new cluster for unknown entity
    Given an ERE service with populated clusters
    When I submit a resolution request for an unknown entity
    Then I receive a response with a new singleton cluster
    And confidence score is 1.0
```

---

## Quality Gates (CI/CD Integration)

### 1. **import-linter** — Enforce Layer Dependencies

**File:** `.importlinter`

```ini
[importlinter]
root_packages = ere

[importlinter:contract:layers]
name = ERE three-layer architecture
type = layers
layers =
    ere.entrypoints
    ere.services
    ere.adapters
    ere.models
```

**Violations blocked:**
- ❌ `ere.models` importing from `ere.services` (reverse dependency)
- ❌ `ere.entrypoints` importing from `ere.adapters` (bypass services)
- ❌ Circular imports between sub-modules

**Run:** `make check-architecture` or `tox -e architecture`

### 2. **pylint** — SOLID + Code Quality

**File:** `.pylintrc`

**Key rules enforced:**
- SRP: max 7 arguments, max 10 attributes, max 20 locals, max 75 statements per function
- Naming: functions are `snake_case`, classes are `PascalCase`
- Complexity: cyclomatic max 10, cognitive max 15
- Duplicates: min 10 lines before flagging

**Run:** `make lint` or `tox -e clean-code`

### 3. **SonarCloud** — Historical Quality Gates

**File:** `sonar-project.properties`

**Quality gates on new code:**
- ✅ 0 critical/blocker issues (must fail if violated)
- ✅ Coverage ≥ 80% (must fail if lower)
- ✅ Duplicated lines ≤ 3%
- ✅ 0 code smells

**Integration:** GitHub PR comments on violations

### 4. **pytest-cov** — Coverage Reporting

**Config:** `pyproject.toml`

```toml
[tool.pytest.ini_options]
addopts = [
  "--cov=src",
  "--cov-report=term-missing",
  "--cov-fail-under=80",
]
```

**Run:** `make test-unit` (HTML report: `htmlcov/index.html`)

---

## File Structure

```
ere/
├── models/
│   ├── __init__.py
│   ├── entity_mention.py       # EntityMention, EntityMentionIdentifier
│   ├── cluster.py              # Cluster, ClusterReference
│   ├── resolution_request.py   # ResolutionRequest (contract)
│   ├── resolution_response.py  # ResolutionResponse (contract)
│   └── threshold_logic.py      # Pure business rules (no I/O)
│
├── adapters/
│   ├── __init__.py
│   ├── resolver/
│   │   ├── abstract_resolver.py      # AbstractResolver interface
│   │   ├── mock_resolver.py          # Test double
│   │   └── basic_resolver.py         # Simple string similarity
│   ├── cluster_repository.py         # Cluster persistence interface
│   ├── redis_adapter.py              # Redis pub/sub client
│   └── entity_deserializer.py        # RDF/JSON/XML parsing
│
├── services/
│   ├── __init__.py
│   ├── abstract_pubsub_resolution_service.py  # Template method
│   ├── redis_resolution_service.py             # Production pub/sub
│   ├── direct_resolution_service.py            # Testing/direct calls
│   └── resolution_orchestrator.py              # High-level workflow
│
└── entrypoints/
    ├── __init__.py
    ├── redis_consumer.py       # Async listener
    ├── direct_api_client.py    # Synchronous wrapper
    └── health_check.py         # Status endpoint (if exposed)

test/
├── unit/
│   ├── models/
│   │   ├── test_entity_mention.py
│   │   ├── test_cluster.py
│   │   └── test_threshold_logic.py
│   ├── adapters/
│   │   ├── test_basic_resolver.py
│   │   ├── test_cluster_repository.py
│   │   └── test_redis_adapter.py
│   ├── services/
│   │   ├── test_abstract_pubsub_service.py
│   │   ├── test_redis_resolution_service.py
│   │   └── test_resolution_orchestrator.py
│   └── entrypoints/
│       ├── test_redis_consumer.py
│       └── test_direct_api_client.py
│
├── features/
│   └── ere/
│       └── entity_resolution.feature
│
└── steps/
    └── test_entity_resolution_steps.py
```

---

## Integration with ERS (Entity Resolution System)

**Request Flow:**

```
ERS Client                Redis Queue         ERE Service
──────────────────────── ──────────────────── ────────────
1. Create request     →  [ere:requests]   →  1. Consume
2. Serialize JSON        (async, fire-forget)  2. Validate
3. Publish to Redis                           3. Resolve
                                              4. Persist
                     ←  [ere:responses]   ←  5. Publish
4. Consume response                          response
5. Parse JSON
6. Store mapping
```

**Guarantees:**

- ✅ **Asynchronous:** Request and response are decoupled
- ✅ **Idempotent:** Same `ereRequestId` returns same outcome (latest)
- ✅ **Eventually consistent:** Responses may arrive out of order
- ✅ **Timeout-aware:** Hard timeout ≤ 5s, soft timeout within signal window

---

## Developer Workflow

### Local Development

```bash
# Install
make install

# Unit tests + coverage
make test-unit

# Lint (pylint, fast, your venv)
make lint

# Full quality checks (tox, isolated)
make all-quality-checks

# Before commit
make test-unit lint check-architecture
```

### CI/CD

```bash
# GitHub Actions
tox -e py312,architecture,clean-code
```

---

## Key Design Decisions

| Decision | Rationale | Trade-off |
|----------|-----------|-----------|
| **Pub/sub async** | Decouples ERS from ERE; enables parallel processing | Slightly higher latency; requires idempotency |
| **Strategy pattern for resolvers** | Easy to plug in new similarity strategies | Adds indirection (extra abstraction layer) |
| **Template method for services** | Reuse orchestration logic across transports (Redis, direct) | More code upfront |
| **Threshold-based decisions** | Simple, deterministic; easy to tune | May create ambiguous matches (handled by client curation) |
| **Strict layering** | Prevents circular dependencies; enforces testability | Feels "over-engineered" for small modules (but pays off) |

---

## References

- **[ERE-OVERVIEW.md](./ERE-OVERVIEW.md)** — High-level technical overview
- **[Sequence Diagrams](./sequence_diagrams/)** — Mermaid flow diagrams (request/response, curation, lookup)
- **[CLAUDE.md](../../CLAUDE.md)** — Meaningfy Clean Code standards + SOLID principles
- **[Cosmic Python](https://www.cosmicpython.com/)** — Book on Clean Architecture for Python

