"""Unit tests for adapters.utils: message parsing utilities."""

import json
from datetime import datetime, timezone

import pytest
from erspec.models.core import EntityMention, EntityMentionIdentifier
from erspec.models.ere import (
    EREErrorResponse,
    EntityMentionResolutionRequest,
    EntityMentionResolutionResponse,
)
from linkml_runtime.dumpers import JSONDumper

from ere.adapters.utils import (
    get_message_object,
    get_request_from_message,
    get_response_from_message,
)

_dumper = JSONDumper()


def _make_request(request_id: str = "utils-test-001") -> EntityMentionResolutionRequest:
    return EntityMentionResolutionRequest(
        entity_mention=EntityMention(
            identifiedBy=EntityMentionIdentifier(
                request_id=request_id,
                source_id="utils-test-src",
                entity_type="http://test.org/Org",
            ),
            content_type="text/turtle",
            content="<>",
        ),
        ere_request_id=request_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def _serialise(obj) -> bytes:
    return _dumper.dumps(obj).encode("utf-8")


def test_get_request_from_message_returns_request():
    raw = _serialise(_make_request("req-parse-01"))
    result = get_request_from_message(raw)
    assert isinstance(result, EntityMentionResolutionRequest)
    assert result.ere_request_id == "req-parse-01"


def test_get_response_from_message_returns_error_response():
    response = EREErrorResponse(
        ere_request_id="resp-parse-01",
        error_type="TestError",
        error_title="Test",
        error_detail="detail",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    raw = _serialise(response)
    result = get_response_from_message(raw)
    assert isinstance(result, EREErrorResponse)
    assert result.ere_request_id == "resp-parse-01"


def test_get_message_object_raises_on_missing_type():
    raw = json.dumps({"ere_request_id": "no-type"}).encode("utf-8")
    with pytest.raises(ValueError, match="message without 'type' field"):
        get_message_object(raw, {})


def test_get_message_object_raises_on_unsupported_type():
    raw = json.dumps({"type": "UnknownClass", "ere_request_id": "x"}).encode("utf-8")
    with pytest.raises(ValueError, match='unsupported message class: "UnknownClass"'):
        get_message_object(raw, {})
