Work Shape Canvas
Prepare Docker-based Infrastructure for Local ERE Development
The Bet

If we package ERE and its required services (Redis and DuckDB) inside a self-contained /infra Docker setup, then any developer can run the full system locally using a single docker compose command, without installing Redis, Python dependencies, or DuckDB on their machine.

This will reduce onboarding friction, eliminate environment drift, and create a stable base for future production hardening.

Appetite

Small–Medium (focused infrastructure slice, no production hardening, no demo automation).

This is not a deployment architecture exercise. It is a deterministic local execution environment.

Problem

Currently, running ERE locally requires manual dependency setup (Python environment, Redis installation, future DuckDB configuration). This:

Creates inconsistency between developer machines

Introduces version drift

Slows onboarding

Makes reproducibility fragile

We need a portable runtime boundary that isolates the host machine from infrastructure concerns.

Core Requirements (Minimum Viable Shape)
1. Infrastructure Folder Contract

All infrastructure artifacts must live under:

/infra

Deliverables:

/infra/Dockerfile

/infra/docker-compose.yml

/infra/.env.local (runtime configuration source)

Optional: /infra/.env.example

No other infra logic outside this folder (except Makefile targets)

2. ERE Container
Build Strategy

Single Dockerfile in /infra

Builds the ERE application image

Installs all required Python dependencies

Copies application code

Defines runtime entrypoint

Entrypoint Strategy

We do not yet know the exact launch command.

Constraint:

The startup command will originate from an application entrypoint located in /entrypoints package.

The Dockerfile must assume a clear, single executable module (e.g. python -m entrypoints.app, or similar).

The exact command can be refined during implementation.

The container must:

Start the ERE service automatically on container startup.

Fail fast if the entrypoint is invalid.

3. Redis Service

Use official Redis image.

Expose standard Redis port (6379).

Internal networking only (no need for public exposure unless required).

No advanced persistence tuning required.

4. DuckDB Service

Even though DuckDB is often embedded, we anticipate needing it.

Minimum shape:

Provide DuckDB availability in a containerised form.

Either:

As a sidecar service (if externalised), or

As part of the ERE container environment (if embedded usage).

The shape decision must prefer simplicity:

If DuckDB is embedded library usage → install inside ERE container.

If external service is required → define minimal compose service.

No optimisation or performance tuning required.

5. Configuration Strategy

ERE must read configuration from:

/infra/.env.local

Compose must:

Load .env.local

Inject environment variables into ERE container

Provide Redis connection settings via environment variables

Example configuration shape (conceptual):

REDIS_HOST=redis
REDIS_PORT=6379
DUCKDB_PATH=/data/app.duckdb
APP_PORT=8000

The system must run correctly using only .env.local.

6. Docker Compose Requirements

docker-compose.yml must:

Define services:

ere

redis

duckdb (if externalised)

Establish internal network automatically

Ensure dependency ordering (e.g. depends_on)

Mount volumes only if necessary

Expose only the ERE service port to host

Success condition:

docker compose -f infra/docker-compose.yml up --build

results in:

Redis running

DuckDB available

ERE service running and reachable

No additional setup required on host machine beyond Docker.

7. Makefile Integration

Add targets:

make infra-build

make infra-up

make infra-down

make infra-logs

No demo targets required.

Makefile must delegate cleanly to docker compose commands and not duplicate configuration logic.

Explicit Non-Goals (Out of Scope)

To keep this minimal and well-shaped:

No Kubernetes

No production-ready security

No TLS

No orchestration beyond compose

No CI pipeline integration

No performance optimisation

No demo automation targets

This is strictly local development infrastructure.

Risks & Unknowns

Entrypoint ambiguity
The /entrypoints structure must stabilise enough to define a deterministic launch command.

DuckDB deployment mode
Decision needed: embedded vs service.
Prefer embedded unless a strong reason exists.

Configuration discipline
The application must correctly externalise configuration via environment variables.
If it currently hardcodes values, refactor may be needed.

Definition of Done

The task is complete when:

On a clean machine with only Docker installed:

docker compose up inside /infra runs the full stack.

No local Redis, Python, or DuckDB installation is required.

ERE service starts automatically.

Configuration is fully externalised via .env.local.

Makefile targets operate correctly.

All infra artifacts live strictly under /infra.

Minimal Value Delivered

One command.
Full system running.
Zero host dependency setup.

That is the smallest coherent vertical slice of infrastructure.