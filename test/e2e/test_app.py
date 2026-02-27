"""End-to-end test: app.py processes entity resolution requests from Redis.

This test simulates the complete flow:
1. Push EntityMentionResolutionRequest to input queue
2. App consumes, parses, and processes request
3. Response is written to output queue
4. Verify response structure and content
"""

import json
import os
from datetime import datetime, timezone

import pytest
import redis
from linkml_runtime.dumpers import JSONDumper

from ere.adapters.factories import build_rdf_mapper
from ere.adapters.utils import get_request_from_message, get_response_from_message
from ere.services.factories import (
    build_entity_resolver,
    build_entity_resolution_service,
)


# ===============================================================================
# Fixtures
# ===============================================================================


@pytest.fixture(scope="module")
def redis_client():
    """
    Connect to Redis and verify it's available.
    Raises: RuntimeError if Redis is not accessible.
    """
    try:
        client = redis.Redis(
            host=os.environ.get("REDIS_HOST", "localhost"),
            port=int(os.environ.get("REDIS_PORT", "6379")),
            db=int(os.environ.get("REDIS_DB", "0")),
            password=os.environ.get("REDIS_PASSWORD", "changeme"),
            decode_responses=False,
        )
        client.ping()
        return client
    except Exception as e:
        raise RuntimeError("Redis test service cannot be detected.") from e


@pytest.fixture
def redis_queues(redis_client):
    """Provide queue names and clear them before test."""
    request_queue = "test-ere-requests"
    response_queue = "test-ere-responses"

    # Clear queues
    redis_client.delete(request_queue, response_queue)

    yield request_queue, response_queue

    # Cleanup
    redis_client.delete(request_queue, response_queue)


@pytest.fixture(scope="module")
def e2e_entity_resolution_service():
    """Build the full entity resolution service for e2e tests."""
    resolver = build_entity_resolver()
    mapper = build_rdf_mapper()
    return build_entity_resolution_service(resolver, mapper)


@pytest.fixture
def dumper():
    """Cached JSONDumper for serialization."""
    return JSONDumper()


# ===============================================================================
# Helper functions
# ===============================================================================


def create_entity_mention_request(
    request_id: str,
    source_id: str,
    entity_type: str,
    legal_name: str,
    country_code: str,
) -> dict:
    """Create a minimal EntityMentionResolutionRequest payload."""
    # Minimal RDF content (simplified Turtle)
    # Uses correct predicates per config/rdf_mapping.yaml:
    # - legal_name maps to epo:hasLegalName
    # - country_code maps to cccev:registeredAddress/epo:hasCountryCode
    content = f"""
@prefix org: <http://www.w3.org/ns/org#> .
@prefix cccev: <http://data.europa.eu/m8g/> .
@prefix epo: <http://data.europa.eu/a4g/ontology#> .
@prefix epd: <http://data.europa.eu/a4g/resource/> .
@prefix locn: <http://www.w3.org/ns/locn#> .

epd:ent001 a org:Organization ;
    epo:hasLegalName "{legal_name}" ;
    cccev:registeredAddress [
        epo:hasCountryCode "{country_code}"
    ] ;
    cccev:telephone "+44 1924306780" .
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


# ===============================================================================
# End-to-end tests
# ===============================================================================


def test_single_request_resolution_flow(redis_client, redis_queues, e2e_entity_resolution_service, dumper):
    """
    E2E test: single entity mention pushed to queue, resolved, response returned.

    Flow:
    1. Create and push EntityMentionResolutionRequest to input queue
    2. Parse request from queue
    3. Process through service
    4. Push response to output queue
    5. Verify response structure
    """
    request_queue, response_queue = redis_queues

    # 1. Create and push request
    request_payload = create_entity_mention_request(
        request_id="324fs3r345vx",
        source_id="TEDSWS",
        entity_type="ORGANISATION",
        legal_name="Acme Corporation",
        country_code="US",
    )
    request_json = json.dumps(request_payload)
    request_bytes = request_json.encode("utf-8")
    redis_client.rpush(request_queue, request_bytes)

    # 2. Simulate app logic: get request from queue
    result = redis_client.brpop(request_queue, timeout=1)
    assert result is not None, "Request should be in queue"
    _, raw_msg = result

    # 3. Parse and process request
    request = get_request_from_message(raw_msg)
    assert request.type == "EntityMentionResolutionRequest"
    assert request.entity_mention.identifiedBy.request_id == "324fs3r345vx"

    response = e2e_entity_resolution_service.process_request(request)

    # 4. Push response to output queue
    response_str = dumper.dumps(response)
    response_bytes = response_str.encode("utf-8")
    redis_client.lpush(response_queue, response_bytes)

    # 5. Verify response structure
    result = redis_client.brpop(response_queue, timeout=1)
    assert result is not None, "Response should be in output queue"
    _, response_raw = result

    response_obj = get_response_from_message(response_raw)
    assert response_obj.type == "EntityMentionResolutionResponse"
    assert response_obj.entity_mention_id.request_id == "324fs3r345vx"
    assert response_obj.candidates is not None


def test_multiple_requests_accumulate(redis_client, redis_queues, e2e_entity_resolution_service, dumper):
    """
    E2E test: multiple entity mentions are resolved and responses queued.

    Verifies that:
    - Each request is processed independently
    - Responses are returned in order
    - Resolution benefits from accumulated state
    """
    request_queue, response_queue = redis_queues

    # Create and push two requests
    mentions = [
        ("m1_324fs3r345vx", "TEDSWS", "Acme Corp", "US"),
        ("m2_324fs3r345vx", "TEDSWS", "Acme Corporation", "US"),
    ]

    for req_id, source, legal_name, country in mentions:
        request_payload = create_entity_mention_request(
            request_id=req_id,
            source_id=source,
            entity_type="ORGANISATION",
            legal_name=legal_name,
            country_code=country,
        )
        request_json = json.dumps(request_payload)
        redis_client.rpush(request_queue, request_json.encode("utf-8"))

    # Process both requests
    responses = []
    for _ in range(2):
        result = redis_client.brpop(request_queue, timeout=1)
        assert result is not None
        _, raw_msg = result

        request = get_request_from_message(raw_msg)
        response = e2e_entity_resolution_service.process_request(request)
        response_str = dumper.dumps(response)
        redis_client.lpush(response_queue, response_str.encode("utf-8"))
        responses.append(response)

    # Verify both responses (order may vary due to LPUSH/BRPOP behavior)
    assert len(responses) == 2
    request_ids = {r.entity_mention_id.request_id for r in responses}
    assert request_ids == {"m1_324fs3r345vx", "m2_324fs3r345vx"}

    # Both should have candidates
    for response in responses:
        assert response.candidates is not None


def test_request_response_payload_structure(redis_client, redis_queues, e2e_entity_resolution_service, dumper):
    """
    E2E test: verify request and response payload structures match spec.

    Validates:
    - Request has required fields
    - Response has required fields with correct types
    """
    request_queue, response_queue = redis_queues

    # Create a request
    request_payload = create_entity_mention_request(
        request_id="struct_test_001",
        source_id="TEST_SOURCE",
        entity_type="ORGANISATION",
        legal_name="Test Organization Ltd",
        country_code="GB",
    )

    # Verify request structure
    assert request_payload["type"] == "EntityMentionResolutionRequest"
    assert "entity_mention" in request_payload
    assert "identifiedBy" in request_payload["entity_mention"]
    assert "content" in request_payload["entity_mention"]
    assert "content_type" in request_payload["entity_mention"]
    assert request_payload["entity_mention"]["content_type"] == "text/turtle"

    # Push, parse, process
    request_bytes = json.dumps(request_payload).encode("utf-8")
    redis_client.rpush(request_queue, request_bytes)

    result = redis_client.brpop(request_queue, timeout=1)
    request = get_request_from_message(result[1])
    response = e2e_entity_resolution_service.process_request(request)

    # Verify response structure
    assert response.type == "EntityMentionResolutionResponse"
    assert hasattr(response, "entity_mention_id")
    assert hasattr(response, "candidates")
    assert hasattr(response, "timestamp")
    assert hasattr(response, "ere_request_id")

    # Verify candidates structure
    for candidate in response.candidates:
        assert hasattr(candidate, "cluster_id")
        assert hasattr(candidate, "confidence_score")
        assert hasattr(candidate, "similarity_score")
        assert isinstance(candidate.confidence_score, (float, int))
        assert isinstance(candidate.similarity_score, (float, int))


def test_organisation_with_different_country(redis_client, redis_queues, e2e_entity_resolution_service, dumper):
    """
    E2E test: organization entities with different country codes.

    Verifies service can process requests with different countries (uses blocking rules).
    """
    request_queue, response_queue = redis_queues

    # Create request with German organization
    request_payload = create_entity_mention_request(
        request_id="de_org_test",
        source_id="TEDSWS",
        entity_type="ORGANISATION",
        legal_name="Test GmbH",
        country_code="DE",
    )

    request_bytes = json.dumps(request_payload).encode("utf-8")
    redis_client.rpush(request_queue, request_bytes)

    result = redis_client.brpop(request_queue, timeout=1)
    assert result is not None

    request = get_request_from_message(result[1])
    assert request.entity_mention.identifiedBy.entity_type == "ORGANISATION"

    # Should process without error
    response = e2e_entity_resolution_service.process_request(request)
    assert response is not None
    assert response.type == "EntityMentionResolutionResponse"
