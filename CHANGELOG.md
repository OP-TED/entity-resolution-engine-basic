# Changelog

All notable changes to the Basic Entity Resolution Engine (Basic ERE) are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

## [1.1.0-rc.6] - 2026-07-16

### Removed
* SonarCloud integration, as it depended on contractor-specific configuration (TEDSWS-528).


## [1.0.0-rc.2] - 2026-06-30

### Changed
* ERSys installation instructions and related documentation improved (TEDSWS-520)
* Contractor-specific references removed from the source code repositories (TEDSWS-528)


## [1.1.0-rc.4] - 2026-06-30

### Changed
* Dockerfile updated to use fully qualified Docker Hub reference for the Python base image


## [1.1.0-rc.3] - 2026-06-10

### Changed
- Package author updated to Publications Office of the European Union
- `poetry.lock` refreshed with updated dependency pins
- Installation instructions updated

## [1.1.0-rc.2] - 2026-05-15

### Added
- Optional TLS support for Redis connections via `REDIS_TLS` environment variable
- Redis adapter extracted as a reusable, standalone component
- `REDIS_PASSWORD` documented in configuration reference
- Environment variable reference section added to configuration documentation

### Changed
- `REQUEST_QUEUE` / `RESPONSE_QUEUE` renamed to `ERSYS_REQUEST_QUEUE` / `ERSYS_RESPONSE_QUEUE` — update `.env` files accordingly
- Dependency versions pinned to exact values for reproducible builds
- Makefile made compatible with macOS `make` tool
- `rdflib` and `pyyaml` moved from development to main dependencies
- `logging.exception` used instead of `logging.error` for exception logging with stack traces


## [1.0.0-rc.1] - 2026-04-21

### Added
- Unit test suite expanded to meet the 80% coverage threshold

### Changed
- Repository layout restructured: `config/`, `demo/`, `pyproject.toml`, `poetry.lock`, and `infra/` consolidated under `src/`; all tooling, Makefile targets, and path references updated accordingly
- Docker: multi-stage wheel-based build with non-root user for improved security and build reproducibility; configuration decoupled from the image and mounted at runtime
- CI: SonarCloud scan made conditional on token availability; coverage report path mapping corrected; integration tests excluded from the tox pipeline to keep unit runs self-contained; staging deployment gated behind explicit dispatch
- Environment variables aligned with ERSys naming convention

## [0.3.0] - 2026-03-04

### Added

**Core Entity Resolution Engine**
- Probabilistic entity resolution using Splink (probabilistic record linkage)
- Incremental clustering with stable, deterministic cluster identifiers (`SHA256(source_id, request_id, entity_type)`)
- Cold-start parameter initialization for Splink comparisons (configurable m/u probabilities per field)
- Expectation-Maximization (EM) training for automatic probabilistic model refinement as mention database grows
- Idempotent processing: re-submitting identical requests yields identical clustering outcomes

**Redis Queue Integration**
- `RedisQueueWorker` for asynchronous message consumption and response publishing
- Support for `EntityMentionResolutionRequest` and `EntityMentionResolutionResponse` message types
- Configurable request/response queue names via environment variables
- Full adherence to ERS–ERE Technical Contract v0.2

**Data Storage & Repositories**
- `DuckDBMentionRepository`: Stores entity mentions with idempotency tracking
- `DuckDBSimilarityRepository`: Caches Splink comparison results for reuse
- `DuckDBClusterRepository`: Manages cluster assignments and lifecycle
- In-memory or persistent DuckDB storage (configurable via `DUCKDB_PATH`)

**RDF Data Ingestion**
- `TurtleRDFMapper` for parsing Turtle-format RDF entity data
- Configurable field extraction via `rdf_mapping.yaml` (predicates, namespaces)
- Support for nested RDF properties (e.g., `registeredAddress/hasCountryCode`)
- Declarative entity type definitions (no hardcoded types)

**Configuration & Customization**
- `resolver.yaml`: Splink comparison rules, cold-start parameters, threshold tuning
- `rdf_mapping.yaml`: RDF field binding and extraction rules per entity type
- Environment variable overrides for deployment flexibility
- CLI argument support for config paths and log levels

**Diagnostic & Observability**
- Comprehensive TRACE-level logging throughout the service
- Training status and parameter visualization (cold-start vs. EM-trained)
- EM training progress logging with m/u probability estimation milestones
- Request/response payload logging for debugging

**Testing Infrastructure**
- Unit tests for adapters (DuckDB repositories, RDF mapper, Splink linker)
- Integration tests for full entity resolution workflow with real adapters
- BDD scenarios (Gherkin) for clustering behaviour and algorithm verification
- End-to-end tests for Redis queue integration and service startup
- Test fixtures for consistent service and mapper setup across test layers
- Stress test framework with synthetic datasets (org-mid.csv) for throughput/latency benchmarking

**Architecture & Code Quality**
- Layered Cosmic Python architecture: models → adapters/services → entrypoints
- Import-linter enforcement of dependency boundaries (no circular imports)
- SOLID principles: Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion
- 80%+ test coverage target on new production code
- Comprehensive docstrings and type hints

**Docker & Deployment**
- Multi-stage Dockerfile for production-ready containerization
- `compose.dev.yaml` for full-stack setup (Redis + ERE service)
- `.env.example` template for configuration

**Documentation**
- README with architecture overview, capabilities, and quickstart
- ERS–ERE Technical Contract specification (PDF)
- Architecture documentation with layered design diagrams
- Algorithm documentation with step-by-step resolution flow
- Configuration reference for resolver and RDF mapping tuning
- Contributing guidelines and branch naming conventions
- CLAUDE.md for development workflow and architecture rules

**Demo Application**
- `demo/demo.py`: Sends synthetic entity mentions and displays clustering results
- Configurable mention datasets with ground-truth clusters
- Queue interaction examples and Redis integration demonstration

