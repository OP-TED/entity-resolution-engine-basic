# Changelog

All notable changes to the Basic Entity Resolution Engine (Basic ERE) are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

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
- `docker-compose.yml` for full-stack setup (Redis + ERE service)
- `.env.example` template for configuration

**Documentation**
- README with architecture overview, capabilities, and quickstart
- ERS–ERE Technical Contract specification (PDF)
- Architecture documentation with layered design diagrams
- Algorithm documentation with step-by-step resolution flow
- Configuration reference for resolver and RDF mapping tuning
- Contributing guidelines and branch naming conventions
- WORKING.md for active task tracking
- CLAUDE.md for development workflow and architecture rules

**Demo Application**
- `demo/demo.py`: Sends synthetic entity mentions and displays clustering results
- Configurable mention datasets with ground-truth clusters
- Queue interaction examples and Redis integration demonstration

### Changed

- Test directory restructured for clarity: `test/steps/` → `test/features/steps/`, `test/adapters/` → `test/unit/`, `test/service/` → `test/unit/adapters/`
- Consolidated logging configuration in `ere/utils/logging.py`
- Entity resolution model training triggered automatically at 50-mention threshold
- Response queue name defaults to `ere-responses` (from original spec)
- Request queue name defaults to `ere-requests` (from original spec)

### Fixed

- Cold-start parameter index mapping for Splink non-null comparison levels
- DuckDB connection cleanup in app.py finally block to prevent resource leaks
- Redis password environment variable handling (default to None, override via `REDIS_PASSWORD`)
- Entity mention idempotency: identical requests return identical cluster assignments

---

