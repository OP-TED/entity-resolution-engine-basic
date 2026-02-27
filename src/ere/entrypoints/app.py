"""
ERE service launcher — entrypoint for local development & Docker.

Reads entity resolution requests from a Redis queue, logs them to stdout,
and produces responses back to another Redis queue.

All configuration is read from environment variables.

Environment variables:
    REQUEST_QUEUE   Redis queue for inbound requests (default: ere-requests)
    RESPONSE_QUEUE  Redis queue for outbound responses (default: ere-responses)
    REDIS_HOST      Redis hostname (default: localhost)
    REDIS_PORT      Redis port (default: 6379)
    REDIS_DB        Redis DB index (default: 0)
    LOG_LEVEL       Python log level name (default: INFO)
"""

import logging
import os
import signal
import sys
from datetime import datetime, timezone

import redis
from linkml_runtime.dumpers import JSONDumper

from ere.adapters.factories import build_rdf_mapper
from ere.adapters.utils import get_request_from_message
from ere.services.factories import (
    build_entity_resolver,
    build_entity_resolution_service,
)
from erspec.models.ere import EREErrorResponse

log = logging.getLogger(__name__)
_dumper = JSONDumper()  # Cache for reuse


def _configure_logging() -> None:
    """Set up logging to stdout with ISO 8601 timestamps."""
    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        stream=sys.stdout,
    )


def main() -> None:
    """
    Main entry point: read requests from Redis queue, log them, produce mock responses.
    """
    _configure_logging()
    log.info("ERE mock service starting")

    # Read configuration from environment
    redis_host = os.environ.get("REDIS_HOST", "localhost")
    redis_port = int(os.environ.get("REDIS_PORT", "6379"))
    redis_db = int(os.environ.get("REDIS_DB", "0"))
    redis_password = os.environ.get("REDIS_PASSWORD", None)
    request_queue = os.environ.get("REQUEST_QUEUE", "ere-requests")
    response_queue = os.environ.get("RESPONSE_QUEUE", "ere-responses")

    log.info(
        "Configuration: redis=%s:%d/%d, request_queue=%s, response_queue=%s",
        redis_host,
        redis_port,
        redis_db,
        request_queue,
        response_queue,
    )

    # Connect to Redis
    try:
        client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
            decode_responses=False,
        )
        client.ping()
        log.info("Connected to Redis")
    except Exception as e:
        log.error(f"Failed to connect to Redis: {e}")
        sys.exit(1)

    # Build resolver, mapper, and service once before the loop
    try:
        log.info("Building entity resolution components")
        resolver = build_entity_resolver()
        mapper = build_rdf_mapper()
        service = build_entity_resolution_service(resolver, mapper)
        log.info("Entity resolution service ready")
    except Exception as e:
        log.error(f"Failed to build entity resolution service: {e}")
        sys.exit(1)

    # Set up signal handling for graceful shutdown
    running = True

    def _handle_shutdown(sig, _frame):
        nonlocal running
        log.info("Received signal %s — stopping service", sig)
        running = False

    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT, _handle_shutdown)

    # Main service loop
    log.info("ERE service ready, listening for requests")
    try:
        while running:
            # Wait for a request (1-second timeout allows checking running flag periodically)
            result = client.brpop(request_queue, timeout=1)
            if not result:
                continue  # Timeout, check running flag again

            _, raw_msg = result

            # Decode and log the request
            request_str = raw_msg.decode("utf-8")
            log.info(f"Received request: {request_str}")

            # Parse and process the request
            try:
                request = get_request_from_message(raw_msg)
                response = service.process_request(request)
            except Exception as e:
                log.error(f"Failed to parse or process request: {e}")
                response = EREErrorResponse(
                    ere_request_id="unknown",
                    error_type=type(e).__name__,
                    error_title="Request processing error",
                    error_detail=str(e),
                    timestamp=datetime.now(timezone.utc),
                )

            # Serialize response using cached LinkML dumper
            response_str = _dumper.dumps(response)

            # Push to response queue
            try:
                client.lpush(response_queue, response_str)
                request_id = getattr(response, "ere_request_id", "unknown")
                log.info(f"Sent response for request_id={request_id}")
            except Exception as e:
                log.error(f"Failed to send response: {e}")

    except KeyboardInterrupt:
        log.info("Service interrupted")
    except Exception as e:
        log.exception(f"Unexpected error in service loop: {e}")
    finally:
        client.close()
        log.info("ERE mock service stopped")


if __name__ == "__main__":
    main()
