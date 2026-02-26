import logging
from datetime import datetime, timezone

from erspec.models.ere import ERERequest, EREResponse, EREErrorResponse

log = logging.getLogger(__name__)


class MockResolver:
    """
    Placeholder resolver for local development and Docker smoke-testing.

    Returns a well-formed EREErrorResponse so the service loop stays healthy
    and the contract is satisfied, while making it obvious that a real resolver
    has not yet been wired in.

    Replace with a concrete AbstractResolver implementation when resolution
    logic is ready.
    """

    def process_request(self, request: ERERequest) -> EREResponse:
        request_id = getattr(request, "ereRequestId", "unknown")
        log.warning(
            "MockResolver.process_request: returning placeholder error response "
            "for request_id=%s — wire a real resolver to enable resolution.",
            request_id,
        )
        return EREErrorResponse(
            ereRequestId=request_id,
            errorTitle="Mock resolver — not implemented",
            errorDetail=(
                "This ERE instance is running with the MockResolver placeholder. "
                "No resolution logic has been configured."
            ),
            errorType="NotImplementedError",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def __call__(self, request: ERERequest) -> EREResponse:
        return self.process_request(request)
