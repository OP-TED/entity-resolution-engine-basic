"""Redis queue entrypoint driver for entity resolution requests."""

import json
import logging
from datetime import datetime, timezone

from linkml_runtime.dumpers import JSONDumper
from erspec.models.ere import EREErrorResponse, EREResponse

from ere.adapters.utils import get_request_from_message
from ere.services.entity_resolution_service import EntityResolutionService

log = logging.getLogger(__name__)


class RedisQueueWorker:
    """Entrypoint: Process entity resolution requests from Redis queue.

    Acts as a driver between Redis infrastructure and the service layer.
    Dependency injection enables testing with mock Redis and services.
    """

    def __init__(  # pylint: disable=too-many-positional-arguments  # redis, service, 3 queue config params; no natural grouping
        self,
        redis_client,
        entity_resolution_service: EntityResolutionService,
        request_queue: str = "ere_requests",
        response_queue: str = "ere_responses",
        queue_timeout: int = 1,
    ):
        """Initialize worker with dependencies."""
        self.redis_client = redis_client
        self.service = entity_resolution_service
        self.request_queue = request_queue
        self.response_queue = response_queue
        self.queue_timeout = queue_timeout
        self._dumper = JSONDumper()

    def process_single_message(self) -> bool:
        """
        Process one message from request queue.

        Returns:
            True if a message was processed, False if timeout.

        Raises:
            Exception: Propagates connection errors.
        """
        # Wait for a request
        queue_message = self.redis_client.brpop(
            self.request_queue, timeout=self.queue_timeout
        )
        if not queue_message:
            return False  # Timeout

        _, raw_msg = queue_message

        # Decode and log
        request_str = raw_msg.decode("utf-8")
        log.info("Received request: %s", request_str)

        # Try to extract request ID from raw message for error responses
        request_id = "unknown"
        try:
            msg_json = json.loads(request_str)
            request_id = msg_json.get("ere_request_id", "unknown")
        except Exception:  # pylint: disable=broad-exception-caught
            pass  # If JSON parse fails, we'll use "unknown" in error response

        # Parse and process
        try:
            request = get_request_from_message(raw_msg)
            response = self.service.process_request(request)
        except Exception as e:  # pylint: disable=broad-exception-caught
            log.exception("Failed to parse or process request")
            response = self._build_error_response(str(e), request_id)

        # Send response
        self._send_response(response)
        return True

    def _send_response(self, response: EREResponse) -> None:
        """Serialize and push response to queue."""
        response_str = self._dumper.dumps(response)
        try:
            self.redis_client.lpush(self.response_queue, response_str)
            request_id = getattr(response, "ere_request_id", "unknown")
            log.info("Sent response for request_id=%s", request_id)
        except Exception:  # pylint: disable=broad-exception-caught
            log.exception("Failed to send response")

    @staticmethod
    def _build_error_response(
        error_detail: str, ere_request_id: str = "unknown"
    ) -> EREErrorResponse:
        """Build error response for request processing failures."""
        log.error("Building error response: %s", error_detail)
        return EREErrorResponse(
            ere_request_id=ere_request_id,
            error_type="ProcessingError",
            error_title="Request processing error",
            error_detail=error_detail,
            timestamp=datetime.now(timezone.utc),
        )
