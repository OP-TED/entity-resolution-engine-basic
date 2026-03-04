# Entity Resolution Engine (ERE)

> A basic implementation of the ERE component of the Entity Resolution System (ERSys).

The **Entity Resolution Engine (ERE)** is an asynchronous microservice that resolves entity
mentions to canonical clusters. It holds *clustering authority* within ERSys: it evaluates
entity mentions, executes resolution logic, and produces clustering outcomes — including the
canonical cluster identifier. Its counterpart, the **Entity Resolution Service (ERS)**, holds
*exposure and integration authority*: it forwards requests, enforces client-facing time budgets,
and persists the latest clustering outcome per mention.

Their cooperation is governed exclusively by the [ERS–ERE Technical Contract](docs/ERS-ERE-System-Technical-Contract.pdf)
(v0.2, Stable, 23 Feb 2026).

---

## Features

| Capability | Description |
|---|---|
| **Entity mention resolution** | Accepts a structured entity mention and returns one or more cluster candidates with similarity and confidence scores |
| **Cluster lifecycle management** | Creates new singleton clusters for unknown entities; assigns known entities to the best-matching cluster |
| **Canonical identifier derivation** | Derives cluster IDs deterministically: `SHA256(concat(source_id, request_id, entity_type))` |
| **Idempotent processing** | Re-submitting the same request (same identifier triad) returns the same clustering outcome |
| **~~Time-budget support~~** | Supports hard and soft timeouts; responds with the best provisional result if the soft deadline expires |
| **~~Curator feedback loop~~** | Accepts authoritative re-assessments; updates cluster state from provisional to final |
| **~~Pluggable resolver strategy~~** | Resolution algorithm is injected via `AbstractResolver`; swap mock, basic, or ML resolvers without touching the service layer |
| **~~Read-only canonical lookup~~** | Lightweight synchronous query returning the canonical cluster for a known entity URI |

---

## Architecture

ERE follows [Cosmic Python](https://www.cosmicpython.com/) layered architecture with a strict
one-way dependency flow:

```
entrypoints → services → models
                       ↘
                       adapters → models
```

| Layer | Path | Responsibility |
|---|---|---|
| **Models** | `src/ere/models/` | Domain entities (`EntityMention`, `ClusterReference`, …), value objects, pure business rules — no I/O |
| **Adapters** | `src/ere/adapters/` | Infrastructure: Redis client, cluster store, `AbstractResolver` implementations |
| **Services** | `src/ere/services/` | Use-case orchestration; owns transaction boundaries and resolution workflow |
| **Entrypoints** | `src/ere/entrypoints/` | Redis pub/sub consumer; thin layer that parses input and delegates to services |

Architectural boundaries are enforced at CI time via `importlinter`. See
[`docs/architecture/`](docs/architecture/) for sequence diagrams, ADRs, and the full
architecture blueprint.

### Async Pub/Sub Interface

```
ERS                   Redis                     ERE
──────────────────    ──────────────────────    ──────────────────────────
Publish request   →   [ere_requests]        →   Consume & validate
                                                 Resolve entity mention
                                                 Publish clustering outcome
Consume response  ←   [ere_responses]       ←   (cluster_id + scores)
```

Requests and responses are JSON-serialised `ERERequest` / `EREResponse` subclasses.
The contract is intentionally decoupled from the transport: any broker that supports
at-least-once delivery and idempotent semantics may be used.

## Installation

### Requirements

- **Python** 3.12+
- **Poetry** (dependency management)
- **Docker** (required for integration tests — used by `testcontainers` to spin up Redis)

### Installation steps

```bash
# Install Poetry if not already present
make install-poetry

# Install all project dependencies (including dev)
make install
```

---

## Usage

### Running the tests

```bash
make test               # All tests (unit + integration)
make test-unit          # Unit tests only (no Docker required)
make test-integration   # Integration tests (requires Docker)
```

### Test Strategy

ERE follows a layered testing approach aligned with Cosmic Python architecture:

| Test Type | Location | Purpose | Coverage |
|---|---|---|---|
| **Unit Tests (adapters)** | `test/adapters/` | Verify individual adapter components (DuckDB repositories, RDF mapper, Splink linker) in isolation | 6+ tests |
| **Unit Tests (services)** | `test/service/` | Validate service-layer use-case orchestration; entity resolution workflow | 15+ tests |
| **Integration Tests** | `test/integration/` | Test EntityResolver with all real adapters (DuckDB, Splink); full entity mention flow with clustering | 8+ tests |
| **BDD Scenarios** | `test/features/` + `test/steps/` | Gherkin feature files + pytest-bdd steps; document resolution algorithm behavior; verify clustering rules and thresholds | 15+ tests |
| **End-to-End Tests** | `test/e2e/` | Full service startup; Redis queue integration; request/response payload structure validation | 4+ tests |
| **Redis Integration** | `test/test_redis_integration.py` | Verify Redis queue operations, environment loading, authentication | 7 tests |

**Total coverage:** 48+ tests across all layers; 53 passed in latest run.

Key testing practices:
- **TDD by default** — write failing tests before implementing features
- **Layer isolation** — each layer tests its own responsibility only
- **Fixture-driven setup** — reusable fixtures in `conftest.py` for service/mapper creation
- **RDF test data** — Turtle fixtures in `test/test_data/` for realistic entity mention testing

### Code quality

```bash
make format             # Auto-format with Ruff
make lint-check         # Lint without modifying files
make lint-fix           # Lint with auto-fix
```

### All available targets

```bash
make help               # List all targets with descriptions
```

### Starting the Redis entrypoint

> **TODO:** CLI wrapper for launching the Redis consumer is not yet implemented.
> See [`src/ere/entrypoints/redis.py`](src/ere/adapters/redis.py) for the current entrypoint.

### Demo: Entity Resolution via Redis Queues

A working demo is available that demonstrates ERE as a black-box service communicating through Redis queues.

```bash
# Prerequisites: Redis must be running, ERE service must be listening
python demo/demo.py
```

The demo:
- Sends 6 synthetic entity mentions to the request queue
- Listens for resolution responses with cluster assignments
- Logs all interactions with timestamps

See [`demo/README.md`](demo/README.md) for detailed configuration, prerequisites, troubleshooting, and example output.

---

## Project structure

```
src/ere/
├── adapters/        # Redis client, cluster store, resolver implementations
├── entrypoints/     # Redis pub/sub consumer
├── models/          # Domain models (via ers-core dependency)
└── services/        # Resolution use-case orchestration

test/
├── features/        # Gherkin BDD feature files
├── steps/           # pytest-bdd step definitions
├── test_data/       # RDF test fixtures (Turtle)
└── conftest.py      # Shared fixtures and test configuration

docs/
├── architecture/    # ERE architecture overview, sequence diagrams, ADRs
└── ERS-ERE-System-Technical-Contract.pdf
```

---

## Contributing

This project follows the [Stream Coding](https://github.com/frmoretto/stream-coding) and
Cosmic Python development methodology. Before starting work:

1. **Read the task file** — check `WORKING.md` for the current task in progress.
2. **Read the architecture docs** — `docs/architecture/ERE-OVERVIEW.md` and the ERS–ERE contract.
3. **Follow the layer rules** — place code in the correct layer; run `make lint-check` to catch violations.
4. **Write tests first** — BDD features for service-layer use cases; unit tests per layer.
5. **Update the task file** — record progress and decisions in `docs/tasks/`.

Branch naming: `feature/<ticket-id>/<short-description>` (e.g. `feature/ERE1-121/mock-resolver`).


## Related documents

- [ERS–ERE Technical Contract v0.2](docs/ERS-ERE-System-Technical-Contract.pdf)
- [ERE Architecture Overview](docs/architecture/ERE-OVERVIEW.md)
- [Cosmic Python Architecture Blueprint](docs/architecture/ERE-COSMIC-PYTHON-ARCHITECTURE.md)
- [Resolution Tools](docs/resolution-tools.md)
