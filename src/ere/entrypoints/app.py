"""
ERE service launcher — entrypoint for local development & Docker.

Reads entity resolution requests from a Redis queue, logs them to stdout,
and produces responses back to another Redis queue.

Configuration is read from environment variables or CLI arguments.

Environment variables:
    REQUEST_QUEUE         Redis queue for inbound requests (default: ere-requests)
    RESPONSE_QUEUE        Redis queue for outbound responses (default: ere-responses)
    REDIS_HOST            Redis hostname (default: localhost)
    REDIS_PORT            Redis port (default: 6379)
    REDIS_DB              Redis DB index (default: 0)
    LOG_LEVEL             Python log level name (default: INFO) — supports TRACE
    RDF_MAPPING_PATH      Path to rdf_mapping.yaml config file
    RESOLVER_CONFIG_PATH  Path to resolver.yaml config file

CLI arguments:
    --log-level           Python log level name (overrides LOG_LEVEL env var)
    --rdf-mapping-path    Path to rdf_mapping.yaml config file
    --resolver-config-path Path to resolver.yaml config file
"""

import argparse
import logging
import signal
import sys

import redis

from ere.adapters.factories import build_rdf_mapper
from ere.entrypoints.queue_worker import RedisQueueWorker
from ere.services.factories import (
    build_entity_resolver,
    build_entity_resolution_service,
)
from ere.utils.logging import configure_logging

log = logging.getLogger(__name__)


def main() -> None:
    """Main entry point: orchestrate service setup and run queue worker."""
    # Parse CLI arguments
    parser = argparse.ArgumentParser(
        description="ERE service: Entity Resolution Engine"
    )
    parser.add_argument(
        "--log-level",
        default=None,
        help="Python log level name (DEBUG, INFO, WARNING, ERROR, CRITICAL, TRACE)",
    )
    parser.add_argument(
        "--rdf-mapping-path",
        default=None,
        help="Path to rdf_mapping.yaml config file",
    )
    parser.add_argument(
        "--resolver-config-path",
        default=None,
        help="Path to resolver.yaml config file",
    )
    args = parser.parse_args()

    configure_logging(log_level=args.log_level)
    log.info("ERE service starting")

    # Read configuration from environment or CLI
    redis_host = os.environ.get("REDIS_HOST", "localhost")
    redis_port = int(os.environ.get("REDIS_PORT", "6379"))
    redis_db = int(os.environ.get("REDIS_DB", "0"))
    redis_password = os.environ.get("REDIS_PASSWORD", None)
    request_queue = os.environ.get("REQUEST_QUEUE", "ere-requests")
    response_queue = os.environ.get("RESPONSE_QUEUE", "ere-responses")

    # Config file paths: CLI takes precedence over environment
    rdf_mapping_path = args.rdf_mapping_path or os.environ.get("RDF_MAPPING_PATH")
    resolver_config_path = args.resolver_config_path or os.environ.get("RESOLVER_CONFIG_PATH")

    log.info(
        "Configuration: redis=%s:%d/%d, request_queue=%s, response_queue=%s",
        redis_host,
        redis_port,
        redis_db,
        request_queue,
        response_queue,
    )
    log.info(
        "Config paths: rdf_mapping=%s, resolver_config=%s",
        rdf_mapping_path or "(default)",
        resolver_config_path or "(default)",
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
        resolver = build_entity_resolver(
            resolver_config_path=resolver_config_path
        )
        mapper = build_rdf_mapper(rdf_mapping_path=rdf_mapping_path)
        service = build_entity_resolution_service(resolver, mapper)
        log.info("Entity resolution service ready")
    except Exception as e:
        log.error(f"Failed to build entity resolution service: {e}")
        sys.exit(1)

    # Create queue worker
    worker = RedisQueueWorker(
        redis_client=client,
        entity_resolution_service=service,
        request_queue=request_queue,
        response_queue=response_queue,
    )

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
            worker.process_single_message()
    except KeyboardInterrupt:
        log.info("Service interrupted")
    except Exception as e:
        log.exception(f"Unexpected error in service loop: {e}")
    finally:
        client.close()
        log.info("ERE service stopped")


if __name__ == "__main__":
    main()
