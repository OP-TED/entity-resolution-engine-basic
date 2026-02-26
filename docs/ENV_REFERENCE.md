# Environment Configuration Reference

## .env.local (Docker Compose)

This file is used by Docker Compose to configure the ERE service for local development.
It is **git-ignored** — each developer has their own version.

### Required Content

```env
# Redis connection
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=changeme

# Redis queue names (entity resolution request/response channels)
REQUEST_QUEUE=ere-requests
RESPONSE_QUEUE=ere-responses

# DuckDB persistent storage
DUCKDB_PATH=/data/app.duckdb

# ERE service port (exposed to host)
APP_PORT=8000

# Python logging level
LOG_LEVEL=INFO
```

### How it's used

1. Docker Compose loads `.env.local` automatically
2. Variables are injected into the ERE container as environment variables
3. `src/ere/entrypoints/app.py` reads all config from env via `os.environ.get()`

### Defaults (if not in .env.local)

| Variable | Default | Notes |
|---|---|---|
| `REDIS_HOST` | `localhost` | Use `redis` inside Docker Compose |
| `REDIS_PORT` | `6379` | Standard Redis port |
| `REDIS_DB` | `0` | Database index (0-15); 0 is default "ere" database |
| `REDIS_PASSWORD` | (none) | **Recommended:** Set a password for security |
| `REQUEST_QUEUE` | `ere-requests` | Incoming entity resolution requests |
| `RESPONSE_QUEUE` | `ere-responses` | Outgoing cluster assignments |
| `DUCKDB_PATH` | `/data/app.duckdb` | Path inside container (volume-mounted) |
| `APP_PORT` | `8000` | Port exposed to host machine |
| `LOG_LEVEL` | `INFO` | DEBUG, INFO, WARNING, ERROR, CRITICAL |

---

## .env.example (Template)

This file is **committed to git** and serves as a template for new developers.

It should contain:
```env
# Copy this file to .env.local and customize as needed

# Redis connection (inside Docker Compose: use 'redis' as hostname)
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

# Redis authentication (recommended for security)
REDIS_PASSWORD=changeme

# Redis queue names for entity resolution
REQUEST_QUEUE=ere_requests
RESPONSE_QUEUE=ere_responses

# DuckDB file path (inside container: /data/app.duckdb)
DUCKDB_PATH=/data/app.duckdb

# ERE service port (host port to expose)
APP_PORT=8000

# Python logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL=INFO
```

---

## Redis Database Structure

**Note on Redis Databases:**

Redis uses numeric database indices (0-15, typically). The ERE system uses:
- **Database 0** (default "ere" database): Contains all entity resolution request/response queues
  - `ere_requests` queue
  - `ere_responses` queue
  - Any future ERE-specific data

To use a different database, change `REDIS_DB` in `.env.local`:
```env
REDIS_DB=1  # Use database 1 instead of 0
```

---

## Code Implementation

### How app.py reads configuration

**File:** `src/ere/entrypoints/app.py` (lines 53-67)

```python
# Read configuration from environment
redis_host = os.environ.get("REDIS_HOST", "localhost")
redis_port = int(os.environ.get("REDIS_PORT", "6379"))
redis_db = int(os.environ.get("REDIS_DB", "0"))
request_queue = os.environ.get("REQUEST_QUEUE", "ere_requests")
response_queue = os.environ.get("RESPONSE_QUEUE", "ere_responses")

log.info(
    "Configuration: redis=%s:%d/%d, request_queue=%s, response_queue=%s",
    redis_host,
    redis_port,
    redis_db,
    request_queue,
    response_queue,
)
```

### How they're used

1. **Request Queue** — app.py listens here for incoming requests:
   ```python
   result = client.brpop(request_queue, timeout=1)
   ```

2. **Response Queue** — app.py sends responses here:
   ```python
   client.lpush(response_queue, response_str)
   ```

---

## Docker Compose Integration

**File:** `infra/docker-compose.yml`

The `.env.local` file is automatically loaded by Docker Compose:

```yaml
services:
  ere:
    # ...
    env_file: .env.local
    # Variables are injected into container environment
```

This means `REQUEST_QUEUE` and `RESPONSE_QUEUE` become available to app.py via `os.environ.get()`.

---

## Local Testing (Without Docker)

To run app.py locally (if Redis is running on localhost):

```bash
# Override queue names if needed
REQUEST_QUEUE=local_requests RESPONSE_QUEUE=local_responses python -m ere.entrypoints.app
```

Or use defaults:
```bash
python -m ere.entrypoints.app
```

---

## Summary

✅ **Code is correctly configured:**
- app.py reads `REQUEST_QUEUE` and `RESPONSE_QUEUE` from env
- Falls back to sensible defaults if not set
- Logs all configuration on startup for visibility

✅ **Configuration files should contain:**
- Both `.env.local` (git-ignored, Docker Compose)
- And `.env.example` (git-tracked, template)
- With all 8 variables listed above