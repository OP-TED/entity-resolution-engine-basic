# Multi-stage build for the Entity Resolution Engine.
# Build context: repository root (one level above /infra)

# =============================================================================
# Fetcher stage: resolve dependencies and build wheels
# =============================================================================
FROM docker.io/library/python:3.12-slim AS fetcher

ARG POETRY_VERSION=">=2.0.0,<3.0.0"

ENV POETRY_NO_INTERACTION=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir "poetry${POETRY_VERSION}" poetry-plugin-export

WORKDIR /app
COPY src/pyproject.toml src/poetry.lock ./

# Export dependencies, build wheels (including git repos), then clean the requirements file
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes \
    && pip wheel -r requirements.txt -w /wheels \
    && sed -i 's/ @ git.*//' requirements.txt

# =============================================================================
# Builder stage: install wheels into a virtual environment
# =============================================================================
FROM docker.io/library/python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Create a virtual environment
RUN python -m venv /app/.venv
ENV PATH="/app/.venv/bin:${PATH}"

# Copy wheels and requirements from fetcher
COPY --from=fetcher /wheels /wheels
COPY --from=fetcher /app/requirements.txt /requirements.txt

# Install dependencies without using the network
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r /requirements.txt

COPY README.md /README.md
COPY src/pyproject.toml src/poetry.lock ./
COPY src/ere ere/
COPY src/config config/

# Install the application itself without re-triggering dependency resolution
RUN pip install --no-deps .


# =============================================================================
# Runtime stage: minimal production image
# =============================================================================
FROM docker.io/library/python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:${PATH}"

RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

WORKDIR /app

# Copy only the virtual environment and necessary app files
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/ere /app/ere
COPY --from=builder /app/config /app/config
# Volume mount point for DuckDB persistent storage
RUN mkdir -p /data && chown appuser:appuser /data

USER appuser

CMD ["python", "-m", "ere.entrypoints.app"]
