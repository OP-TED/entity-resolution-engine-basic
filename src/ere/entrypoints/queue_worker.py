"""Redis queue entrypoint driver for entity resolution requests."""

import logging
from datetime import datetime, timezone

from linkml_runtime.dumpers import JSONDumper

from ere.adapters.utils import get_request_from_message
from ere.services.entity_resolution_service import EntityResolutionService
from erspec.models.ere import EREErrorResponse, EREResponse

log = logging.getLogger(__name__)


class RedisQueueWorker:
    """Entrypoint: Process entity resolution requests from Redis queue.

    Acts as a driver between Redis infrastructure and the service layer.
    Dependency injection enables testing with mock Redis and services.
    """

    def __init__(
        self,
        redis_client,
        entity_resolution_service: EntityResolutionService,
        request_queue: str = "ere-requests",
        response_queue: str = "ere-responses",
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
        result = self.redis_client.brpop(self.request_queue, timeout=self.queue_timeout)
        if not result:
            return False  # Timeout

        _, raw_msg = result

        # Decode and log
        request_str = raw_msg.decode("utf-8")
        log.info(f"Received request: {request_str}")

        # Parse and process
        try:
            request = get_request_from_message(raw_msg)
            response = self.service.process_request(request)
        except Exception as e:
            log.error(f"Failed to parse or process request: {e}")
            response = self._build_error_response(str(e))

        # Send response
        self._send_response(response)
        return True

    def _send_response(self, response: EREResponse) -> None:
        """Serialize and push response to queue."""
        response_str = self._dumper.dumps(response)
        try:
            self.redis_client.lpush(self.response_queue, response_str)
            request_id = getattr(response, "ere_request_id", "unknown")
            log.info(f"Sent response for request_id={request_id}")
        except Exception as e:
            log.error(f"Failed to send response: {e}")

    @staticmethod
    def _build_error_response(error_detail: str) -> EREErrorResponse:
        """Build error response for request processing failures."""
        return EREErrorResponse(
            ere_request_id="unknown",
            error_type="ProcessingError",
            error_title="Request processing error",
            error_detail=error_detail,
            timestamp=datetime.now(timezone.utc),
        )
