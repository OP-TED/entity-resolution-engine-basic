# ERE Demo - Indirect Redis Client

This demo demonstrates the Entity Resolution Engine (ERE) as an indirect client communicating through Redis queues.

## Overview

The demo:
- Connects to Redis (checking connectivity first)
- Creates 6 synthetic entity mentions
- Sends them as `EntityMentionResolutionRequest` messages to the request queue
- Listens for `EntityMentionResolutionResponse` messages from the response queue
- Logs all interactions with timestamps

The demo treats ERE as a black box service accessible only through Redis message queues. This is useful for:
- Testing the queue-based infrastructure in isolation
- Demonstrating service-to-service communication patterns


## Configuration

Configuration is loaded from `.env.local` (or environment variables):

| Variable | Default | Purpose |
|----------|---------|---------|
| `REDIS_HOST` | `redis` | Redis hostname (use `localhost` for local testing) |
| `REDIS_PORT` | `6379` | Redis port |
| `REDIS_DB` | `0` | Redis database number |
| `REDIS_PASSWORD` | `changeme` | Redis password |
| `REQUEST_QUEUE` | `ere-requests` | Queue name for incoming requests |
| `RESPONSE_QUEUE` | `ere-responses` | Queue name for outgoing responses |

The script tries the configured host first, then falls back to `localhost` if the host is `redis` (Docker), making it work both locally and in Docker.

## Prerequisites

1. **Redis must be running** on the configured host/port
2. **ERE service must be running** (or at least the queue worker must be processing messages)
3. **Project dependencies installed** via Poetry: `poetry install`

## Running the Demo

### 1. With Docker Compose (recommended)

Start the full stack including Redis and ERE:

```bash
cd /home/greg/PROJECTS/ERS/ere-basic
docker-compose -f infra/docker-compose.yml up -d
```

Wait for services to be ready (check logs):

```bash
docker-compose -f infra/docker-compose.yml logs -f
```

### 2. Locally (development)

If you're running Redis locally (e.g., Docker container on `localhost:6379`):

```bash
# Ensure Redis is running
redis-cli ping  # should return "PONG"

# Run the demo
cd /home/greg/PROJECTS/ERS/ere-basic
python3 demo/demo.py
```

Or with Poetry:

```bash
poetry run python3 demo/demo.py
```

**Runtime**: Approximately 5-35 seconds (5s sending + up to 30s waiting for responses).
The demo sends 6 messages with 1-second delays between them, then waits for responses.

## Example Output

```
2026-03-01 12:34:56 [INFO] Loading configuration...
2026-03-01 12:34:56 [INFO] Redis config: host=localhost, port=6379, db=0
2026-03-01 12:34:56 [INFO] Queue names: request=ere-requests, response=ere-responses
2026-03-01 12:34:56 [INFO] Checking Redis connectivity...
2026-03-01 12:34:56 [INFO] ✓ Redis is available
2026-03-01 12:34:56 [INFO] Clearing request and response queues...
2026-03-01 12:34:56 [INFO] Sending 6 entity mentions...
2026-03-01 12:34:56 [INFO]   → Sent request m1: Acme Corp (US) [Mention 1 - initial mention]
2026-03-01 12:34:56 [INFO]   → Sent request m2: Acme Corporation (US) [Mention 2 - high similarity to m1 (sim=0.8)]
...
2026-03-01 12:34:56 [INFO] Listening for responses...
2026-03-01 12:34:56 [INFO] ✓ Response received for m1:
2026-03-01 12:34:56 [INFO]   Type: EntityMentionResolutionResponse
2026-03-01 12:34:56 [INFO]   Timestamp: 2026-03-01T12:34:56.123456+00:00
2026-03-01 12:34:56 [INFO]   Candidates:
2026-03-01 12:34:56 [INFO]     1. Cluster m1: confidence=0.0000, similarity=0.0000
...
2026-03-01 12:34:57 [INFO] Demo complete. Received 6/6 responses.
2026-03-01 12:34:57 [INFO] ✓ All responses received successfully!
```

## Demo Data

The demo sends 6 synthetic mentions based on the flow in ALGORITHM.md:

| ID | Name | Country | Description |
|----|------|---------|-------------|
| m1 | Acme Corp | US | Initial mention, creates singleton cluster |
| m2 | Acme Corporation | US | High similarity to m1 (0.8), extends cluster |
| m3 | Global Industries Ltd | GB | New entity, creates new cluster |
| m4 | Global Industries | GB | High similarity to m3 (0.99), extends cluster |
| m5 | Acme Inc | US | Similar to m2 (0.81), extends Acme cluster |
| m6 | Global Ltd | GB | Similar to m3/m4 (0.9), extends Global cluster |

Expected clustering:
- **Cluster 1**: {m1, m2, m5} - Acme organizations
- **Cluster 2**: {m3, m4, m6} - Global organizations

### Message Timing

**Important**: The demo inserts a **1-second delay** between sending messages. This ensures they are processed sequentially in the order sent. Since the entity resolution algorithm depends on the order of processing (incremental clustering), this delay is crucial for predictable, reproducible clustering results.

Without the delay, messages could be processed out-of-order, leading to different clustering assignments.



## Message Format

### Request (EntityMentionResolutionRequest)

```json
{
  "type": "EntityMentionResolutionRequest",
  "entity_mention": {
    "identifiedBy": {
      "request_id": "m1",
      "source_id": "DEMO",
      "entity_type": "ORGANISATION"
    },
    "content": "@prefix org: <http://www.w3.org/ns/org#> ...",
    "content_type": "text/turtle"
  },
  "timestamp": "2026-03-01T12:34:56.123456+00:00",
  "ere_request_id": "m1:01"
}
```

### Response (EntityMentionResolutionResponse)

```json
{
  "type": "EntityMentionResolutionResponse",
  "entity_mention_id": {
    "request_id": "m1",
    "source_id": "DEMO",
    "entity_type": "ORGANISATION"
  },
  "candidates": [
    {
      "cluster_id": "m1",
      "confidence_score": 0.0,
      "similarity_score": 0.0
    }
  ],
  "timestamp": "2026-03-01T12:34:56.234567+00:00",
  "ere_request_id": "m1:01"
}
```

## Troubleshooting

### "Redis unavailable" error

**Check Redis connectivity:**
```bash
redis-cli -h localhost -p 6379 ping
```

If it returns `PONG`, Redis is running. If not:

- **Docker**: `docker run -d -p 6379:6379 redis:latest`
- **Local Redis**: `brew install redis && brew services start redis` (macOS)
- **Docker Compose**: Ensure the service is running: `docker-compose -f infra/docker-compose.yml up redis`

### Timeout waiting for responses

**Possible causes:**
- ERE service is not running (no worker to process requests)
- Request queue name doesn't match ERE's configured queue name
- ERE worker crashed or stopped processing

**Check ERE logs:**
```bash
docker-compose -f infra/docker-compose.yml logs ere
```

### Password authentication fails

**Edit Redis connection parameters:**

Option 1: Modify `.env.local`:
```bash
REDIS_PASSWORD=your_password
```

Option 2: Set environment variable:
```bash
export REDIS_PASSWORD=your_password
python3 demo/demo.py
```

## Design Notes

- **No direct Python API**: The demo uses Redis as the sole communication channel
- **Message logging**: Every request sent and response received is logged with timestamp
- **Connectivity check**: The demo verifies Redis is accessible before sending messages
- **Queue cleanup**: Request and response queues are cleared at the start of the demo
- **Timeout handling**: The demo waits up to 30 seconds for responses, then reports the count received
- **Docker fallback**: If the configured Redis host is "redis" (Docker), the demo tries localhost as a fallback for local development

## Related Files

- `ALGORITHM.md` - Entity resolution algorithm explanation (source of demo data)
- `.env.local` - Configuration template with defaults
- `infra/docker-compose.yml` - Docker Compose setup for full stack
- `test/e2e/test_app.py` - Integration tests showing request/response patterns
