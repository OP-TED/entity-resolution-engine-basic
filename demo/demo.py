#!/usr/bin/env python3
"""
Demo: Indirect Redis client for ERE (Entity Resolution Engine).

This demo connects to ERE through the Redis queue infrastructure (no direct Python API).
It demonstrates:
1. Checking Redis connectivity
2. Sending EntityMentionResolutionRequest messages to the queue
3. Listening for EntityMentionResolutionResponse messages
4. Logging all interactions

The example uses 6 synthetic mentions from ALGORITHM.md that cluster into 2 groups:
  - Cluster 1: {1, 2, 5}  (organizations with high similarity)
  - Cluster 2: {3, 4, 6}  (different organizations, also highly similar)
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import redis

# ===============================================================================
# Configuration
# ===============================================================================

def load_env_file(env_path: str = None) -> dict:
    """Load configuration from .env.local or environment variables."""
    config = {}

    # Try to load from .env.local if it exists
    if env_path is None:
        env_path = Path(__file__).parent.parent / "infra" / ".env.local"

    if Path(env_path).exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if "=" in line:
                        key, value = line.split("=", 1)
                        config[key.strip()] = value.strip()

    # Environment variables override .env.local
    config["REDIS_HOST"] = os.environ.get("REDIS_HOST", config.get("REDIS_HOST", "localhost"))
    config["REDIS_PORT"] = int(os.environ.get("REDIS_PORT", config.get("REDIS_PORT", "6379")))
    config["REDIS_DB"] = int(os.environ.get("REDIS_DB", config.get("REDIS_DB", "0")))
    config["REDIS_PASSWORD"] = os.environ.get("REDIS_PASSWORD", config.get("REDIS_PASSWORD", "changeme"))
    config["REQUEST_QUEUE"] = os.environ.get("REQUEST_QUEUE", config.get("REQUEST_QUEUE", "ere-requests"))
    config["RESPONSE_QUEUE"] = os.environ.get("RESPONSE_QUEUE", config.get("RESPONSE_QUEUE", "ere-responses"))

    return config


# ===============================================================================
# Logging Setup
# ===============================================================================

def setup_logging():
    """Configure logging with timestamps."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger(__name__)


# ===============================================================================
# Redis Connection
# ===============================================================================

def check_redis_connectivity(host: str, port: int, db: int, password: str) -> redis.Redis:
    """
    Check Redis connectivity and return client.

    Attempts connection to specified host first, then fallback to localhost
    if configured host is "redis" (Docker).

    Raises:
        RuntimeError: If Redis is not accessible.
    """
    hosts_to_try = [host]

    # Fallback: if configured host is "redis" (Docker), also try localhost
    if host == "redis":
        hosts_to_try.append("localhost")

    last_error = None
    for try_host in hosts_to_try:
        try:
            client = redis.Redis(
                host=try_host,
                port=port,
                db=db,
                password=password,
                decode_responses=False,
            )
            client.ping()
            return client
        except Exception as e:
            last_error = e
            continue

    raise RuntimeError(
        f"Redis unavailable. Tried hosts: {hosts_to_try}, port: {port}, db: {db}"
    ) from last_error


# ===============================================================================
# Request/Response Handling
# ===============================================================================

def create_entity_mention_request(
    request_id: str,
    source_id: str,
    entity_type: str,
    legal_name: str,
    country_code: str,
) -> dict:
    """
    Create an EntityMentionResolutionRequest payload.

    Uses simplified RDF/Turtle format with entity metadata.
    """
    content = f"""@prefix org: <http://www.w3.org/ns/org#> .
@prefix cccev: <http://data.europa.eu/m8g/> .
@prefix epo: <http://data.europa.eu/a4g/ontology#> .
@prefix epd: <http://data.europa.eu/a4g/resource/> .

epd:ent{request_id} a org:Organization ;
    epo:hasLegalName "{legal_name}" ;
    cccev:registeredAddress [
        epo:hasCountryCode "{country_code}"
    ] .
"""

    return {
        "type": "EntityMentionResolutionRequest",
        "entity_mention": {
            "identifiedBy": {
                "request_id": request_id,
                "source_id": source_id,
                "entity_type": entity_type,
            },
            "content": content.strip(),
            "content_type": "text/turtle",
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ere_request_id": f"{request_id}:01",
    }


def parse_response(response_bytes: bytes) -> dict:
    """Parse JSON response from Redis."""
    return json.loads(response_bytes.decode("utf-8"))


# ===============================================================================
# Demo Data (from ALGORITHM.md)
# ===============================================================================

DEMO_MENTIONS = [
    {
        "request_id": "m1",
        "source_id": "DEMO",
        "entity_type": "ORGANISATION",
        "legal_name": "Acme Corp",
        "country_code": "US",
        "description": "Mention 1 - initial mention",
    },
    {
        "request_id": "m2",
        "source_id": "DEMO",
        "entity_type": "ORGANISATION",
        "legal_name": "Acme Corporation",
        "country_code": "US",
        "description": "Mention 2 - high similarity to m1 (sim=0.8)",
    },
    {
        "request_id": "m3",
        "source_id": "DEMO",
        "entity_type": "ORGANISATION",
        "legal_name": "Global Industries Ltd",
        "country_code": "GB",
        "description": "Mention 3 - different entity, new cluster",
    },
    {
        "request_id": "m4",
        "source_id": "DEMO",
        "entity_type": "ORGANISATION",
        "legal_name": "Global Industries",
        "country_code": "GB",
        "description": "Mention 4 - high similarity to m3 (sim=0.99)",
    },
    {
        "request_id": "m5",
        "source_id": "DEMO",
        "entity_type": "ORGANISATION",
        "legal_name": "Acme Inc",
        "country_code": "US",
        "description": "Mention 5 - similar to m2 (sim=0.81), extends cluster 1",
    },
    {
        "request_id": "m6",
        "source_id": "DEMO",
        "entity_type": "ORGANISATION",
        "legal_name": "Global Ltd",
        "country_code": "GB",
        "description": "Mention 6 - similar to m3/m4 (sim=0.9), extends cluster 2",
    },
]


# ===============================================================================
# Main Demo
# ===============================================================================

def main():
    """Run the Redis-based ERE demo."""
    logger = setup_logging()

    # Load configuration
    logger.info("Loading configuration...")
    config = load_env_file()
    logger.info(
        f"Redis config: host={config['REDIS_HOST']}, "
        f"port={config['REDIS_PORT']}, db={config['REDIS_DB']}"
    )
    logger.info(
        f"Queue names: request={config['REQUEST_QUEUE']}, "
        f"response={config['RESPONSE_QUEUE']}"
    )

    # Check Redis connectivity
    logger.info("Checking Redis connectivity...")
    try:
        redis_client = check_redis_connectivity(
            host=config["REDIS_HOST"],
            port=config["REDIS_PORT"],
            db=config["REDIS_DB"],
            password=config["REDIS_PASSWORD"],
        )
        logger.info("✓ Redis is available")
    except RuntimeError as e:
        logger.error(f"✗ Redis check failed: {e}")
        return 1

    # Clear queues
    logger.info("Clearing request and response queues...")
    redis_client.delete(config["REQUEST_QUEUE"], config["RESPONSE_QUEUE"])

    # Send demo requests
    logger.info(f"Sending {len(DEMO_MENTIONS)} entity mentions...")
    request_ids = []

    for mention in DEMO_MENTIONS:
        request = create_entity_mention_request(
            request_id=mention["request_id"],
            source_id=mention["source_id"],
            entity_type=mention["entity_type"],
            legal_name=mention["legal_name"],
            country_code=mention["country_code"],
        )

        message_bytes = json.dumps(request).encode("utf-8")
        redis_client.rpush(config["REQUEST_QUEUE"], message_bytes)
        request_ids.append(mention["request_id"])

        logger.info(
            f"  → Sent request {mention['request_id']}: "
            f"{mention['legal_name']} ({mention['country_code']}) "
            f"[{mention['description']}]"
        )

        # Wait 1 second between messages to ensure sequential processing
        time.sleep(1)

    logger.info("")
    logger.info("Listening for responses...")
    logger.info("-" * 80)

    # Listen for responses
    responses_received = {}
    timeout = 30  # seconds
    start_time = time.time()

    while len(responses_received) < len(request_ids):
        elapsed = time.time() - start_time
        if elapsed > timeout:
            logger.warning(f"Timeout after {timeout}s. Received {len(responses_received)}/{len(request_ids)} responses.")
            break

        # Try to get a response with short timeout
        result = redis_client.brpop(config["RESPONSE_QUEUE"], timeout=1)

        if result is not None:
            _, response_bytes = result
            response = parse_response(response_bytes)

            req_id = response["entity_mention_id"]["request_id"]
            responses_received[req_id] = response

            logger.info(f"\n✓ Response received for {req_id}:")
            logger.info(f"  Type: {response['type']}")
            logger.info(f"  Timestamp: {response['timestamp']}")

            source_id = response["entity_mention_id"]["source_id"]
            entity_type = response["entity_mention_id"]["entity_type"]
            logger.info(f"  Mention: ({source_id}, {req_id}, {entity_type})")

            logger.info(f"  Candidates:")

            for i, candidate in enumerate(response.get("candidates", []), 1):
                logger.info(
                    f"    {i}. Cluster {candidate['cluster_id']}: "
                    f"confidence={candidate['confidence_score']:.4f}, "
                    f"similarity={candidate['similarity_score']:.4f}"
                )

    logger.info("-" * 80)
    logger.info(f"\nDemo complete. Received {len(responses_received)}/{len(request_ids)} responses.")

    # Summary
    if len(responses_received) == len(request_ids):
        logger.info("✓ All responses received successfully!")
        return 0
    else:
        logger.warning(f"✗ Missing {len(request_ids) - len(responses_received)} response(s).")
        return 1


if __name__ == "__main__":
    sys.exit(main())
