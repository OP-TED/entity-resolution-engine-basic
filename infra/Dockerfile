# ── ERE application image ──────────────────────────────────────────────────
# Builds the Entity Resolution Engine service for local development.
# Requires only Docker — no local Python, Redis, or DuckDB installation.
#
# Build context: repository root (one level above /infra)
# Usage:  docker compose -f infra/docker-compose.yml up --build
# ───────────────────────────────────────────────────────────────────────────

FROM python:3.12-slim

# git is required to fetch the ers-core dependency from GitHub
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry (locked to major version 2)
RUN pip install --no-cache-dir "poetry>=2.0.0,<3.0.0"

WORKDIR /app

# ── Dependency layer (cached unless pyproject.toml / poetry.lock change) ───
COPY pyproject.toml poetry.lock* ./

# Install into system Python (no virtualenv needed inside the container)
RUN poetry config virtualenvs.create false \
    && poetry install --without dev --no-root --no-interaction

# ── Application source ──────────────────────────────────────────────────────
COPY README.md ./
COPY src/ ./src/

# Install the ere package itself
RUN poetry install --without dev --no-interaction

# ── Runtime ─────────────────────────────────────────────────────────────────
# Fail fast: Python will exit immediately if the module cannot be imported.
CMD ["python", "-m", "ere.entrypoints.app"]
