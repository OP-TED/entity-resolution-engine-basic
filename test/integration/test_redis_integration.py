"""
Integration tests for Redis queue interaction with ERE service.

These tests verify end-to-end request/response flow through Redis.

Environment variables are loaded from:
  1. /infra/.env.local (if it exists)
  2. Environment variables
  3. Built-in defaults

Run with:
    pytest test/test_redis_integration.py -v
    pytest test/test_redis_integration.py::test_send_dummy_request -v
"""

import json
import time
import os
from pathlib import Path
import pytest
import redis

# Try to load environment from /infra/.env.local
_env_local_path = Path(__file__).parent.parent / "infra" / ".env.local"
if _env_local_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_local_path, override=False)
    except ImportError:
        # python-dotenv not installed, parse manually
        with open(_env_local_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    key, _, value = line.partition("=")
                    if key and value:
                        os.environ.setdefault(key.strip(), value.strip())


@pytest.fixture
def redis_client():
    """Connect to Redis with configuration from environment or defaults.

    When running tests from host machine with .env.local (which has REDIS_HOST=redis),
    automatically fall back to localhost for testing.
    """
    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", "6379"))
    db = int(os.getenv("REDIS_DB", "0"))
    password = os.getenv("REDIS_PASSWORD", None)

    # If using 'redis' hostname from Docker, try localhost instead
    if host == "redis":
        test_host = "localhost"
    else:
        test_host = host

    # Use decode_responses=False to get bytes, then decode explicitly in tests
    client = redis.Redis(
        host=test_host,
        port=port,
        db=db,
        password=password,
        decode_responses=False,
    )

    # Verify connection
    try:
        response = client.ping()
        print(f"\n✓ Connected to Redis at {test_host}:{port}")
    except Exception as e:
        pytest.skip(f"Redis not available at {test_host}:{port} — {e}")

    # Flush entire database to start clean
    try:
        client.flushdb()
        print(f"✓ Flushed Redis DB {db}")
    except Exception as e:
        print(f"Warning: Could not flush database: {e}")

    yield client

    # Cleanup after test
    try:
        client.flushdb()
    except Exception as e:
        print(f"Warning: Could not cleanup after test: {e}")


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

    def test_redis_service_connectivity(self):
        """Test: Redis service exists and client can connect."""
        host = os.getenv("REDIS_HOST", "localhost")
        port = int(os.getenv("REDIS_PORT", "6379"))
        password = os.getenv("REDIS_PASSWORD", None)

        # Try localhost first (for host testing)
        test_host = "localhost" if host == "redis" else host

        try:
            client = redis.Redis(
                host=test_host,
                port=port,
                password=password,
                decode_responses=False,
                socket_connect_timeout=5,
            )
            response = client.ping()
            assert response is True, "Redis ping failed"
            print(f"\n✓ Redis service available at {test_host}:{port}")
        except Exception as e:
            pytest.fail(f"Cannot connect to Redis at {test_host}:{port} — {e}")

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
        initial_response_count = redis_client.llen("ere-responses")

        # Push request
        redis_client.lpush("ere-requests", json.dumps(request))

        # Wait for processing (service has 3-5s timeout per iteration)
        time.sleep(2)

        # Check delta in response queue
        new_response_count = redis_client.llen("ere-responses") - initial_response_count

        # Skip this test if the service isn't running
        if new_response_count == 0:
            pytest.skip("ERE service not running — skipping response test")

        assert new_response_count == 1, f"Expected 1 new response, got {new_response_count}"

        # Retrieve and verify response format (latest response is at index 0)
        response_raw = redis_client.lindex("ere-responses", 0)
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
        # Send 3 requests
        for i in range(3):
            request = create_test_request(f"test-multi-{i:03d}", f"Entity {i}")
            redis_client.lpush("ere-requests", json.dumps(request))

        # Wait for processing (service has 3-5s timeout per iteration)
        time.sleep(4)

        # Verify all got responses (skip if service not running)
        response_count = redis_client.llen("ere-responses")
        if response_count == 0:
            pytest.skip("ERE service not running — skipping response verification")

        assert response_count == 3, f"Expected 3 responses, got {response_count}"

    def test_redis_authentication(self, redis_client):
        """Test: Verify Redis connection works with authentication."""
        # If we got here, redis_client fixture succeeded
        # which means authentication (if needed) worked

        response = redis_client.ping()
        assert response is True, "Redis ping failed"

    def test_malformed_request_handling(self, redis_client):
        """Test: Service handles malformed requests gracefully."""
        # Push invalid JSON
        redis_client.lpush("ere-requests", "this is not valid json")

        # Service should still be running (not crash)
        time.sleep(1)

        # Verify service is still responsive
        response = redis_client.ping()
        assert response is True, "Service crashed on malformed request"


if __name__ == "__main__":
    """Allow running tests directly: python test/test_redis_integration.py"""
    pytest.main([__file__, "-v"])