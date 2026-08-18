# Infrastructure

Deployment and infrastructure files for the Entity Resolution Engine.

## Structure

```
infra/
├── .env.example      # Environment variable template
├── compose.dev.yaml  # Docker Compose for local development
├── Dockerfile        # Multi-stage build (builder + runtime)
└── README.md
```

## Services

| Service | Purpose | Port |
|---|---|---|
| `ere` | Entity Resolution Engine (Redis queue worker) | — (no HTTP API) |
| `redis` | Message queue for ERE requests/responses | 6379 |
| `redisinsight` | Redis GUI (development tool) | 5540 |

## Usage

All commands run from the repo root via `make`:

```bash
make infra-build          # Build the ERE Docker image
make infra-up             # Start services (docker compose up -d)
make infra-down           # Stop and remove containers and networks
make infra-down-volumes   # Stop services and remove volumes (clean slate)
make infra-rebuild        # Rebuild images and start services
make infra-rebuild-clean  # Rebuild from scratch (no cache)
make infra-logs           # Follow service logs
make infra-watch          # Start services with file watching (sync src/ and config/)
```

### File watching (development)

`make infra-watch` uses Docker Compose's `watch` feature to sync source code and
configuration changes into the running container without a full rebuild:

- **Source changes** (`src/`) are synced live into the container
- **Config changes** (`config/`) are synced live into the container
- **Dependency changes** (`pyproject.toml`, `poetry.lock`) trigger a full rebuild

> **Note:** ERE is a long-running queue worker, not an HTTP server with hot-reload.
> After syncing, restart the container to pick up changes: `docker compose -f infra/compose.dev.yaml restart ere`

### Manual build

```bash
docker build -f infra/Dockerfile -t ere:latest .
```

## Configuration

Environment variables are loaded from `infra/.env`. See `infra/.env.example` for available options. To set up:

```bash
cp infra/.env.example infra/.env
```

### Resolver configuration

Entity resolution behaviour is configured via YAML files in the top-level `config/` directory:

- **[resolver.yaml](../config/resolver.yaml)** — Splink comparisons, cold-start parameters, blocking rules, thresholds
- **[rdf_mapping.yaml](../config/rdf_mapping.yaml)** — RDF namespace bindings, field extraction rules, entity type definitions

See the [configuration README](../config/README.md) for detailed tuning guidance.
