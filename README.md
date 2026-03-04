# Basic Entity Resolution Engine (Basic ERE)

[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=meaningfy-ws_entity-resolution-engine-basic&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=meaningfy-ws_entity-resolution-engine-basic)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=meaningfy-ws_entity-resolution-engine-basic&metric=coverage)](https://sonarcloud.io/summary/new_code?id=meaningfy-ws_entity-resolution-engine-basic)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/downloads/)

> A basic implementation of the ERE component of the Entity Resolution System (ERSys).

## Overview

The **Basic Entity Resolution Engine (Basic ERE)** is an asynchronous microservice that implements entity resolution for predefined entity types. It supports incremental clustering with stable cluster identifiers.

Its primary purpose is to interact with the Entity Resolution System (ERSys). It adheres to the [ERS–ERE Technical Contract](docs/ERS-ERE-System-Technical-Contract.pdf), which establishes the communication protocol between ERE and ERS (part of ERSys) via a message queue (Redis). It also provides a foundation for other ERE implementations.

### Dependencies

ERE relies on **ers-core** (from [entity-resolution-spec](https://github.com/OP-TED/entity-resolution-spec)), which provides:
- **Shared domain models** — Common entity types and concepts across the ERSys ecosystem
- **ERE contract message models** — Standardized request/response structures for ERE–ERS communication (`EntityMentionResolutionRequest`, `EntityMentionResolutionResponse`, `EREErrorResponse`)

This ensures type-safe, versioned communication between ERE and other ERSys components.

### Capabilities

* **Entity mention resolution**: Accepts a structured entity mention and returns one or more cluster candidates with similarity and confidence scores

* **Cluster lifecycle management**: Creates new singleton clusters for unknown entities; assigns known entities to the best-matching cluster

* **Canonical identifier derivation**: Derives cluster IDs deterministically: `SHA256(concat(source_id, request_id, entity_type))`

* **Idempotent processing**: Re-submitting the same request (same identifier triad) returns the same clustering outcome

* **Cold-start and incremental resolution**: Builds cluster structure organically without prior training data and doesn't require global reclustering.

* **RDF data ingestion**: Accepts RDF (Turtle) entity data with configurable field mapping and extraction

* **Declarative entity type support**: Arbitrary entity types specified via configuration files (no hardcoding)

* **Automatic probabilistic model training**: Trains the entity resolution model on-the-fly as the mention database grows (Expectation-Maximisation based)


For detailed documentation, see:
- [**Architecture**](docs/architecture.md) — layered design, sequence diagrams, ADRs
- [**Algorithm**](docs/algorithm.md) — incremental probabilistic entity linking (to be written)
- [**Configuration**](docs/configuration.md) — field mapping, model tuning, Splink setup (to be written)



## Installation

### Requirements

- **Python** 3.12+
- **make**
- **Poetry** (dependency management)
- **Docker**

### Quickstart

```bash
# Install all Python dependencies (Poetry is required)
make install

# Build the ERE Docker image
make infra-build

# Start the full stack: Redis + ERE service
make infra-up
```

For detailed setup instructions, see `Make targets`.



## Usage

ERE has no HTTP API. It communicates exclusively through Redis message queues:
- **Request queue**: `ere_requests` — ERS publishes `EntityMentionResolutionRequest` messages
- **Response queue**: `ere_responses` — ERE publishes `EntityMentionResolutionResponse` or `EREErrorResponse` messages


### Make targets

### Configuration (Resolver and Mapper)

Entity resolution behaviour is configured via two YAML files:
- **Resolver configuration** (`infra/.env.local`): Splink comparisons, cold-start parameters, similarity thresholds
- **RDF mapping** (`test/resources/rdf_mapping.yaml`): RDF namespace bindings, field extraction rules, entity type definitions

For detailed configuration options and tuning, see [docs/configuration.md](docs/configuration.md).

### Examples

A working demo is available that demonstrates ERE as a black-box service communicating through Redis queues.

```bash
# Prerequisites: Redis must be running, ERE service must be listening
python demo/demo.py                              # Uses org-tiny.json (8 mentions, 2 clusters)
python demo/demo.py --data demo/data/mentions_100b.json  # 100 mentions, realistic clustering
```

The demo:
- Loads entity mentions from JSON datasets stored in `demo/data/`
- Sends mentions to the request queue via RDF Turtle messages
- Listens for resolution responses with cluster assignments
- Logs all interactions with timestamps and outputs a clustering summary

**Datasets**: Multiple datasets available:
- `org-tiny.json` (default) — 8 organization mentions
- `mentions_100b.json` — 100 business entities (corresponds to `test/stress/data/mentions_100b.csv`)
- `mentions_1000.json` — 1,000 business entities (corresponds to `test/stress/data/mentions_1000.csv`)

See [`demo/README.md`](demo/README.md) for datasets, configuration, logging, prerequisites, troubleshooting, and example output.



## Project

### Structure

```
src/ere/
├── adapters/        # Redis client, cluster store, resolver implementations
├── entrypoints/     # Redis pub/sub consumer
├── models/          # Domain models (entities, value objects, exceptions)
└── services/        # Resolution use-case orchestration

test/
├── features/        # Gherkin BDD feature files
├── steps/           # pytest-bdd step definitions
├── integration/     # Integration tests (full stack)
├── e2e/             # End-to-end tests (Redis queue flows)
├── test_data/       # RDF test fixtures (Turtle)
└── conftest.py      # Shared fixtures and test configuration

docs/
├── architecture/    # ERE architecture, sequence diagrams, ADRs
├── tasks/           # Implementation task logs
├── ERS-ERE-System-Technical-Contract.pdf
└── *.md             # Topic documentation

infra/
├── Dockerfile       # ERE service image definition
├── docker-compose.yml  # Full stack (Redis + ERE)
├── .env.example     # Configuration template
└── .env.local       # Local runtime config (git-ignored)
```

### Tooling

| Category | Tools |
|---|---|
| Language | Python 3.12+ |
| Entity resolution engine | Splink (probabilistic record linkage) |
| Data storage | DuckDB (embedded) |
| Message broker | Redis |
| Package management | Poetry |
| Build & task runner | Make |
| Containerisation | Docker + Docker Compose |
| Test runner | pytest, pytest-bdd (Gherkin) |
| Code quality | Ruff (formatting, linting), Pylint (style/SOLID) |
| Architecture enforcement | importlinter (dependency validation) |



## Testing

ERE has several test layers aligned with its Cosmic Python architecture.

| Test Type | Location | Purpose |
|---|---|---|
| **Unit Tests (adapters)** | `test/unit/adapters/` | Verify individual adapter components (DuckDB repositories, RDF mapper, Splink linker) in isolation |
| **Unit Tests (services)** | `test/unit/services/` | Validate service-layer use-case orchestration; entity resolution workflow |
| **Integration Tests** | `test/integration/` | Test EntityResolver with all real adapters (DuckDB, Splink); full entity mention flow with clustering |
| **BDD Scenarios** | `test/features/` + `test/features/steps/` | Gherkin feature files + pytest-bdd step definitions; document resolution algorithm behaviour; verify clustering rules and thresholds |
| **End-to-End Tests** | `test/e2e/` | Full service startup; Redis queue integration; request/response payload structure validation |
| **Stress Tests** | `test/stress/` | Load testing and performance profiling; throughput and latency benchmarks |

**Stress Test Datasets**: Committed to `test/stress/data/` with ground-truth clustering for reproducible benchmarking.
See [Stress Test Datasets README](test/stress/data/README.md) for dataset descriptions and usage.

### Running Tests

```bash
# All tests (unit + integration; requires Docker)
make test

# Unit tests only (no Docker required)
make test-unit

# Integration tests (requires Docker)
make test-integration

# Code formatting and linting
make format             # Auto-format with Ruff
make lint-check         # Lint without modifying files
make lint-fix           # Lint with auto-fix
```

### Key Testing Practices

- **TDD by default** — write failing tests before implementing features
- **Layer isolation** — each layer tests its own responsibility only
- **Fixture-driven setup** — reusable fixtures in `conftest.py` for service/mapper creation


## Related Documents

- [ERS–ERE Technical Contract v0.2](docs/ERS-ERE-System-Technical-Contract.pdf)
- [ERE Architecture](docs/architecture.md)
- [ERE Cosmic Python Architecture Blueprint](docs/architecture/ERE-COSMIC-PYTHON-ARCHITECTURE.md)
- [Resolution Tools](docs/resolution-tools.md)



## Contributing

Contributions are welcome. Please open an issue before submitting a pull request.

- Follow the existing code style (run `make lint-check` before pushing)
- Write tests for new behaviour (BDD features or unit tests)
- Keep commits small and well-described
- Branch naming: `feature/<ticket>/<short-description>` (e.g. `feature/ERS1-124/conflict-detection`)

For active tasks and current work, see [WORKING.md](WORKING.md).
For development workflow and architecture guidelines, see [CLAUDE.md](CLAUDE.md).
