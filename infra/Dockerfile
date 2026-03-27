# Multi-stage build for the Entity Resolution Engine.
# Build context: repository root (one level above /infra)

# =============================================================================
# Builder stage: install dependencies
# =============================================================================
FROM python:3.12-slim AS builder

ARG POETRY_VERSION=">=2.0.0,<3.0.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1

# git is required to fetch the ers-spec dependency from GitHub
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir "poetry${POETRY_VERSION}"

WORKDIR /app

COPY pyproject.toml poetry.lock ./

RUN poetry install --without dev --no-root

COPY README.md ./
COPY src/ ./src/

RUN poetry install --without dev

# =============================================================================
# Runtime stage: minimal image
# =============================================================================
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:${PATH}"

RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

WORKDIR /app

COPY --from=builder /app/.venv .venv
COPY --from=builder /app/src src
COPY config/ ./config/

# Volume mount point for DuckDB persistent storage
RUN mkdir -p /data && chown appuser:appuser /data

USER appuser

CMD ["python", "-m", "ere.entrypoints.app"]
