"""
Tests the abstract definitions about the ERE service.

In practice, this module tests the ERE contract specification, by using a mock resolver and a mock
service client (which calls the resolver directly, bypassing any network interaction concerns).

Both the mock client and the mock resolver behave as specified in the ERE contract (and in the Gherkin scenarios).

TODO: tests with rejections
TODO: tests idempotency

TODO: several test functions do exactly the same thing across different layers, factorise them into a common
module.
"""

import pytest
from assertpy import assert_that
from ere_test import (
    EPD_NS,
    EPO_NS,
    ORG_NS,
    MockEREClient,
    catch_response,
    entity_id_2_cluster_uri,
    extract_resource_rdf,
    prefix_common_namespaces,
    create_timestamp,
)
from pyparsing import Path
from rdflib import Graph

from ere.entrypoints import AbstractClient
from ere.models.core import (
    EntityMentionResolutionRequest,
    EntityMentionResolutionResponse,
    EntityMention,
    EntityMentionIdentifier,
    ClusterReference,
    EREErrorResponse,
    FullRebuildRequest,
    FullRebuildResponse,
)


# TODO: add Gherkin annotations
def test_known_entity_resolution(mock_ere_client: AbstractClient):
    """
    Scenario: A resolution request returns existing cluster candidate references
    """

    test_entity_uri = (
        f"{EPD_NS}id_2023-S-210-661238_ReviewerOrganisation_LLhJHMi9mby8ixbkfyGoWj"
    )

    expected_cluster = ClusterReference(
        clusterId=f"{EPD_NS}id_2023-S-210-662860_ReviewerOrganisation_LLhJHMi9mby8ixbkfyGoWj_Cluster",
        confidenceScore=0.98,
    )
    expected_alt_cluster = ClusterReference(
        clusterId=f"{EPD_NS}id_2023-S-210-661238_ReviewerOrganisation_LLhJHMi9mby8ixbkfyGoWj_alt_Cluster",
        confidenceScore=0.80,
    )

    test_entity_mention = EntityMention(
        identifier=EntityMentionIdentifier(
            requestId=test_entity_uri,
            sourceId="test-module",
            entityType=f"{ORG_NS}Organization",
        ),
        # Not important here, the mock resolver just looks up static test data
        # TODO: validation of ID/content match
        contentType="text/turtle",
        content="<foo>",
    )

    test_req = EntityMentionResolutionRequest(
        entityMention=test_entity_mention,
        ereRequestId="test-known-entity-resolution-001",
        timestamp=create_timestamp(),
    )

    mock_ere_client.push_request(test_req)
    entity_resolution = catch_response(
        mock_ere_client, test_req.ereRequestId, EntityMentionResolutionResponse
    )

    assert_that(
        entity_resolution.entityMentionId,
        "Resolution response has the source entity mention ID",
    ).is_equal_to(test_entity_mention.identifier)

    candidate_clusters = entity_resolution.candidates

    assert_that(
        candidate_clusters, "Resolution response has the expected candidate clusters"
    ).contains(expected_cluster, expected_alt_cluster)


def test_unknown_entity_resolution(mock_ere_client: AbstractClient):
    """
    Scenario: An unknown entity resolves to itself

    An unknown entity, with no equivalents known to ERE results into a new cluster with the
    entity itself as canonical entity.

    TODO: With the mock resolver, we don't test the case that this happens due to low confidence
    matches. We'll probably need this path with an actual resolver implementation.
    """

    test_entity_uri = f"{ORG_NS}foo_organization_999"

    test_entity_mention = EntityMention(
        identifier=EntityMentionIdentifier(
            requestId=test_entity_uri,
            sourceId="test-module",
            entityType=f"{ORG_NS}Organization",
        ),
        # Not important here, the mock resolver just looks up static test data
        # TODO: validation of ID/content match
        contentType="text/turtle",
        content="<foo>",
    )

    test_req = EntityMentionResolutionRequest(
        entityMention=test_entity_mention,
        ereRequestId="test-unknown-entity-resolution-001",
        timestamp=create_timestamp(),
    )

    mock_ere_client.push_request(test_req)
    entity_resolution = catch_response(
        mock_ere_client, test_req.ereRequestId, EntityMentionResolutionResponse
    )

    candidate_clusters = entity_resolution.candidates

    assert_that(
        candidate_clusters, "Resolution response has a single candidate cluster"
    ).is_length(1)
    candidate_cluster = candidate_clusters[0]

    assert_that(
        candidate_cluster.clusterId, "The candidate cluster has the expected ID"
    ).is_equal_to(entity_id_2_cluster_uri(test_entity_mention.identifier))
    assert_that(
        candidate_cluster.confidenceScore,
        "The candidate cluster has a confidence score of 1",
    ).is_equal_to(1)


def test_ere_acknowledges_rebuild_request(mock_ere_client: AbstractClient):
    """
    Scenario: The ERE acknowledges a rebuild request
    """

    rebuild_request = FullRebuildRequest(
        ereRequestId="test-ere-acknowledges-rebuild-request-001",
        timestamp=create_timestamp(),
    )

    mock_ere_client.push_request(rebuild_request)

    # Does all the assertions we want here
    catch_response(mock_ere_client, rebuild_request.ereRequestId, FullRebuildResponse)


def test_ere_still_working_after_rebuild(mock_ere_client: AbstractClient):
    """
    Scenario: The ERE keeps resolving entities as usually after a rebuild request
    """

    # First, send a rebuild request
    rebuild_request = FullRebuildRequest(
        ereRequestId="test-ere-still-working-after-rebuild-001",
        timestamp=create_timestamp(),
    )

    mock_ere_client.push_request(rebuild_request)
    catch_response(mock_ere_client, rebuild_request.ereRequestId, FullRebuildResponse)

    # Now just repeat previous tests
    test_known_entity_resolution(mock_ere_client)
    test_unknown_entity_resolution(mock_ere_client)


def test_ere_replies_with_error_response_to_malformed_request(
    mock_ere_client: AbstractClient,
):
    """
    Scenario: The ERE replies with an error response to a malformed request
    """
    # Send a malformed request (content type is unsupported)
    malformed_request = EntityMentionResolutionRequest(
        ereRequestId="test-bad-resolution-req-001",
        entityMention=EntityMention(
            identifier=EntityMentionIdentifier(
                requestId="", sourceId="test-module", entityType="FooType"
            ),  # Malformed part
            contentType="text/turtle",
            content="<foo>",
        ),
        timestamp=create_timestamp(),
    )

    mock_ere_client.push_request(malformed_request)
    error_response = catch_response(
        mock_ere_client, malformed_request.ereRequestId, EREErrorResponse
    )

    assert_that(
        error_response.errorTitle, "The response has the expected error title"
    ).contains("MockResolver, unsupported entity type")
    assert_that(
        error_response.errorDetail, "The response has the expected error detail"
    ).contains("MockResolver, unsupported entity type")
    assert_that(error_response.errorType, "The response has an error type").is_equal_to(
        "ValueError"
    )


@pytest.fixture
def mock_ere_client() -> AbstractClient:
    return MockEREClient()
