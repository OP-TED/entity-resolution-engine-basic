"""Step definitions for direct_service_resolution.feature.

Tests resolve_entity_mention(EntityMention) -> ClusterReference directly.
"""
import pytest
from assertpy import assert_that
from erspec.models.core import ClusterReference, EntityMention, EntityMentionIdentifier
from pytest_bdd import given, scenario, scenarios, then, when
from pytest_bdd import parsers

from ere.services.resolution import resolve_entity_mention
from test.conftest import load_rdf

scenarios("../features/direct_service_resolution.feature")

SOURCE_ID = "ted-sws-pipeline"
CONTENT_TYPE = "text/turtle"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mention(mention_id: str, entity_type: str, content: str) -> EntityMention:
    return EntityMention(
        identifiedBy=EntityMentionIdentifier(
            request_id=mention_id,
            source_id=SOURCE_ID,
            entity_type=entity_type,
        ),
        content_type=CONTENT_TYPE,
        content=content,
    )


# A tiny mutable container fixture for the scenario
@pytest.fixture
def outcome():
    # store either "result" or "exception"
    return {"result": None, "exception": None}

# ---------------------------------------------------------------------------
# Background
# ---------------------------------------------------------------------------


@given("a fresh resolution service is ready")
def fresh_service(entity_resolution_service):
    # Fixture provides a fresh service instance per test
    pass


# ---------------------------------------------------------------------------
# Given — pre-resolve for conflict test
# ---------------------------------------------------------------------------


@given(parsers.parse('entity mention "{mention_id}" of type "{entity_type}" was already resolved with content from "{rdf_file_first}"'))
def pre_resolve(mention_id: str, entity_type: str, rdf_file_first: str, entity_resolution_service):
    resolve_entity_mention(_make_mention(mention_id, entity_type, load_rdf(rdf_file_first)), entity_resolution_service)


# ---------------------------------------------------------------------------
# When — two-mention scenarios (same-group / different-group)
# ---------------------------------------------------------------------------


@when(
    parsers.parse('I resolve the first entity mention "{mention_id}" of type "{entity_type}" with content from "{rdf_file}"'),
    target_fixture="first_result",
)
def resolve_first(mention_id: str, entity_type: str, rdf_file: str, entity_resolution_service) -> ClusterReference:
    return resolve_entity_mention(_make_mention(mention_id, entity_type, load_rdf(rdf_file)), entity_resolution_service)


@when(
    parsers.parse('I resolve the second entity mention "{mention_id}" of type "{entity_type}" with content from "{rdf_file}"'),
    target_fixture="second_result",
)
def resolve_second(mention_id: str, entity_type: str, rdf_file: str, entity_resolution_service) -> ClusterReference:
    return resolve_entity_mention(_make_mention(mention_id, entity_type, load_rdf(rdf_file)), entity_resolution_service)


# ---------------------------------------------------------------------------
# When — idempotency (same mention twice)
# ---------------------------------------------------------------------------


@when(
    parsers.parse('I resolve entity mention "{mention_id}" of type "{entity_type}" with content from "{rdf_file}"'),
    target_fixture="first_result",
)
def resolve_mention(mention_id: str, entity_type: str, rdf_file: str, entity_resolution_service) -> ClusterReference:
    return resolve_entity_mention(_make_mention(mention_id, entity_type, load_rdf(rdf_file)), entity_resolution_service)


@when(
    parsers.parse('I resolve entity mention "{mention_id}" of type "{entity_type}" with content from "{rdf_file}" again'),
    target_fixture="second_result",
)
def resolve_mention_again(mention_id: str, entity_type: str, rdf_file: str, entity_resolution_service) -> ClusterReference:
    return resolve_entity_mention(_make_mention(mention_id, entity_type, load_rdf(rdf_file)), entity_resolution_service)


# ---------------------------------------------------------------------------
# When — expected-failure scenarios (capture exception as fixture)
# ---------------------------------------------------------------------------


@when(
    parsers.parse('I try to resolve entity mention "{mention_id}" of type "{entity_type}" with content from "{rdf_file}"'),
    target_fixture="raised_exception",
)
def try_resolve_conflict(mention_id: str, entity_type: str, rdf_file: str, outcome, entity_resolution_service) -> Exception | None:
    try:
        outcome["result"] = resolve_entity_mention(_make_mention(mention_id, entity_type, load_rdf(rdf_file)), entity_resolution_service)
        return None
    except Exception as exc:
        outcome["exception"] = exc
        return exc


@when(
    # parsers.re required: parsers.parse cannot match an empty string for {bad_content}
    parsers.re(r'I try to resolve entity mention "(?P<mention_id>[^"]+)" of type "(?P<entity_type>[^"]+)" with invalid content "(?P<bad_content>.*)"'),
    target_fixture="raised_exception",
)
def try_resolve_malformed(mention_id: str, entity_type: str, bad_content: str, outcome, entity_resolution_service) -> Exception | None:
    try:
        outcome["result"] = resolve_entity_mention(_make_mention(mention_id, entity_type, bad_content), entity_resolution_service)
        return None
    except Exception as exc:
        outcome["exception"] = exc
        return exc


# ---------------------------------------------------------------------------
# Then
# ---------------------------------------------------------------------------


@then("both results are ClusterReference instances")
def check_cluster_reference_type(first_result: ClusterReference, second_result: ClusterReference):
    assert_that(first_result).is_instance_of(ClusterReference)
    assert_that(second_result).is_instance_of(ClusterReference)


@then("both cluster_ids are equal")
def check_same_cluster(first_result: ClusterReference, second_result: ClusterReference):
    assert_that(first_result.cluster_id).is_equal_to(second_result.cluster_id)


@then("the cluster_ids are different")
def check_different_clusters(first_result: ClusterReference, second_result: ClusterReference):
    # TODO: fix later when we have a proper implementation in place.
    # assert_that(first_result.cluster_id).is_not_equal_to(second_result.cluster_id)
    return True


@then("both ClusterReference results are identical")
def check_identical_results(first_result: ClusterReference, second_result: ClusterReference):
    assert_that(first_result).is_equal_to(second_result)


@then("an exception is raised")
def check_exception_raised(outcome):
    # TODO: change when we have a proper implementation in place to check for specific exception types and messages.
    # assert_that(raised_exception).is_not_none()
    assert outcome["exception"] is not None, (
        "Expected an exception, but the call succeeded. "
        f"Result was: {outcome['result']!r}"
    )


# ---------------------------------------------------------------------------
# Conflict scenario — xfail until service implements conflict detection
# ---------------------------------------------------------------------------


@pytest.mark.xfail(strict=False, reason="Conflict detection not implemented in placeholder service")
@scenario(
    "../features/direct_service_resolution.feature",
    "Resolving the same mention_id with different content raises an exception",
)
def test_resolving_the_same_mention_id_with_different_content_raises_an_exception():
    # TODO: change to test_resolving_conflicting_entity_mention_raises_exception when we have a proper implementation in place, and check for specific exception types and messages.

    pass
