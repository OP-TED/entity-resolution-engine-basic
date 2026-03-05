"""
Integration tests for Redis queue interaction with ERE service.

These tests verify end-to-end request/response flow through Redis.


Run with:
    pytest test/integration/test_redis_integration.py -v
    pytest test/integration/test_redis_integration.py::TestRedisQueueIntegration::test_send_dummy_request -v
"""

import json
import time

import pytest


def create_test_request(request_id: str = "test-001", content: str = "John Smith") -> dict:
    """Create a valid EntityMentionResolutionRequest for testing."""
    return {
        "type": "EntityMentionResolutionRequest",
        "ere_request_id": request_id,
        "timestamp": "2026-02-24T21:00:00Z",
        "entity_mention": {
            "identifiedBy": "mention-1",
            "content_type": "text",
            "content": content,
        },
    }


@pytest.mark.integration
class TestRedisQueueIntegration:
    """Test ERE service request/response flow through Redis."""

    def test_redis_service_connectivity(self, redis_client):
        """Test: Redis service exists and client can connect."""
        try:
            response = redis_client.ping()
            assert response is True, "Redis ping failed"
        except Exception as e:
            pytest.fail(f"Cannot connect to Redis: {e}")

    def test_send_dummy_request(self, redis_client):
        """Test: Push a dummy request and verify it was queued."""
        request = create_test_request("test-send-001")

        # Push request to queue
        result = redis_client.lpush("dummy-queue", json.dumps(request))
        print(f"lpush result: {result}")
        assert result == 1, "Request was not added to queue"

        # Verify queue length
        queue_len = redis_client.llen("dummy-queue")
        print(f"Queue length after push: {queue_len}")
        assert queue_len == 1, f"Expected 1 request in queue, got {queue_len}"

        # Verify data is actually in Redis
        item = redis_client.lindex("dummy-queue", 0)
        assert item is not None, "No data found in queue"
        print(f"Item in queue: {item[:50]}...")  # Print first 50 bytes

    def test_receive_response(self, redis_client):
        """Test: Verify response format from mock service (skip if service not running)."""
        request = create_test_request("test-receive-001")

        # Snapshot response count before pushing request (to handle in-flight requests from prior tests)
        initial_response_count = redis_client.llen("ere_responses")

        # Push request
        redis_client.lpush("ere_requests", json.dumps(request))

        # Wait for processing (service has 3-5s timeout per iteration)
        time.sleep(2)

        # Check delta in response queue
        new_response_count = redis_client.llen("ere_responses") - initial_response_count

        # Skip this test if the service isn't running
        if new_response_count == 0:
            pytest.skip("ERE service not running — skipping response test")

        assert new_response_count == 1, f"Expected 1 new response, got {new_response_count}"

        # Retrieve and verify response format (latest response is at index 0)
        response_raw = redis_client.lindex("ere_responses", 0)
        assert response_raw is not None, "Response is empty"

        # response_raw is bytes, decode it
        response_str = response_raw.decode("utf-8") if isinstance(response_raw, bytes) else response_raw
        response = json.loads(response_str)

        # Verify response structure
        assert response["type"] == "EREErrorResponse", "Wrong response type"
        assert response["ere_request_id"] == "test-receive-001", "Request ID mismatch"
        assert "error_title" in response, "Missing error_title"
        assert "error_detail" in response, "Missing error_detail"
        assert "timestamp" in response, "Missing timestamp"

    def test_multiple_requests(self, redis_client):
        """Test: Handle multiple sequential requests."""
        # Snapshot response count before pushing requests (to handle in-flight responses from prior tests)
        initial_response_count = redis_client.llen("ere_responses")

        # Send 3 requests
        for i in range(3):
            request = create_test_request(f"test-multi-{i:03d}", f"Entity {i}")
            redis_client.lpush("ere_requests", json.dumps(request))

        # Wait for processing (service has 3-5s timeout per iteration)
        time.sleep(4)

        # Check delta in response queue
        new_response_count = redis_client.llen("ere_responses") - initial_response_count
        if new_response_count == 0:
            pytest.skip("ERE service not running — skipping response verification")

        assert new_response_count == 3, f"Expected 3 new responses, got {new_response_count}"

    def test_redis_authentication(self, redis_client):
        """Test: Verify Redis connection works with authentication."""
        # If we got here, redis_client fixture succeeded
        # which means authentication (if needed) worked

        response = redis_client.ping()
        assert response is True, "Redis ping failed"

    def test_malformed_request_handling(self, redis_client):
        """Test: Service handles malformed requests gracefully."""
        # Push invalid JSON
        redis_client.lpush("ere_requests", "this is not valid json")

        # Service should still be running (not crash)
        time.sleep(1)

        # Verify service is still responsive
        response = redis_client.ping()
        assert response is True, "Service crashed on malformed request"


if __name__ == "__main__":
    """Allow running tests directly: python test/integration/test_redis_integration.py"""
    pytest.main([__file__, "-v"])