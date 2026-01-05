"""
Tests the :class:`RedisResolutionService` and :class:`RedisEREClient` with the mock resolver.
"""

import logging
from typing import Generator

import pytest
import redis
from assertpy import assert_that
from ere_test import (EPD_NS, ORG_NS, MockResolver, catch_response,
                      prefix_common_namespaces)
from rdflib import Graph
from testcontainers.redis import RedisContainer

from ere.entrypoints import AbstractClient
from ere.entrypoints.redis import RedisEREClient
from ere.models.ers_core import (CanonicalEntity, Entity,
                                 EntityResolutionRequest,
                                 EntityResolutionResponse, ErrorResponse)
from ere.services.redis import RedisResolutionService

log = logging.getLogger ( __name__ )



@pytest.mark.integration
def test_known_entity_resolution ( mock_ere_client: AbstractClient ):
	"""
	Scenario: A known entity returns the canonical entity it's equivalent to
	"""
	log.info ( "test_known_entity_resolution: starting" )
	test_entity = Entity (
		id = f"{EPD_NS}id_2023-S-210-661238_ReviewerOrganisation_LLhJHMi9mby8ixbkfyGoWj",
		type = f"{ORG_NS}Organization"
	)
	# TODO: fill the entity with test data
	test_req = EntityResolutionRequest (
    requestId = "test-known-entity-resolution-001",
		entity = test_entity,
		originator = "test-module"
	)

	mock_ere_client.push_request ( test_req )
	entity_resolution = catch_response ( mock_ere_client, test_req.requestId, EntityResolutionResponse )

	assert_that ( entity_resolution.sourceEntityId, "Resolution response has the source entity ID" )\
	  .is_equal_to ( test_entity.id )
	
	assert_that ( entity_resolution.confidenceLevel, "Resolution response has a confidence score" )\
	  .is_equal_to ( 0.98 )	

	canonical_entity: CanonicalEntity = entity_resolution.canonicalEntity
	assert_that ( canonical_entity, "We have a canonical entity in the resolution response" )\
		.is_not_none ()

	assert_that ( canonical_entity.id, "Canonical entity has the expected URI" ).\
	  is_equal_to ( f"{EPD_NS}id_2023-S-210-662860_ReviewerOrganisation_LLhJHMi9mby8ixbkfyGoWj" )
	
	# TODO: this is true for the basic/mockup ERE, in general, returning a result in a given format
	# is not a requirement
	assert_that ( canonical_entity.entityDataFormat, "Canonical entity has the expected data format" )\
	  .is_equal_to ( "text/turtle" )	

	# TODO: import the sparql test utility
	graph = Graph ()
	graph.parse ( data = canonical_entity.entityData, format = 'turtle' )

	for assertion_label, sparql_assertion in [ 
		( 
			"Canonical entity has the correct name",
		  """?ent epo:hasLegalName            "Комисия за защита на конкуренцията"@bg """
		),
		(
			"Canonical entity has the correct email",
		  """?ent epo:hasPrimaryContactPoint/cccev:email "delovodstvo@cpc.bg" """
		),

		(
			"Canonical entity has the correct street address",
		  """?ent cccev:registeredAddress/locn:thoroughfare   "бул. Витоша № 18" """
		)
	]:
		sparql_ask = """
			ASK WHERE {
				BIND ( <%s> AS ?ent ).
				%s
			}
		"""
		sparql_ask = prefix_common_namespaces ( sparql_ask )
		sparql_ask = sparql_ask % ( canonical_entity.id, sparql_assertion )
		assert_that ( graph.query ( sparql_ask ).askAnswer, assertion_label ).is_true ()



@pytest.mark.integration
def test_ere_replies_with_error_response_to_malformed_request ( mock_ere_client: AbstractClient ):
	"""
	Scenario: The ERE replies with an error response to a malformed request
	"""
	# Send a malformed request (missing entity)
	malformed_request = EntityResolutionRequest (
		requestId = "test-bad-resolution-req-001",
		entity = Entity (
			id = "",
			type = "FooType"
		),  # Malformed part
		originator = "test-module"
	)
	
	mock_ere_client.push_request ( malformed_request )
	error_response = catch_response ( mock_ere_client, malformed_request.requestId, ErrorResponse )

	assert_that ( error_response.errorTitle, "The response has the expected error title" )\
		.contains ( "without entity data/RDF" )
	assert_that ( error_response.errorDetail, "The response has the expected error detail" )\
		.contains ( "without entity data/RDF" )
	assert_that ( error_response.errorType, "The response has an error type" )\
		.is_equal_to ( "ValueError" )
	

@pytest.fixture ( autouse = True )
def create_mock_service ( redisdb_client: redis.Redis ) -> Generator[ None, None, None ]:
	"""
	As in similar cases, the service fixture isn't directly used by the tests, in fact, 
	here the client uses Redis networking.
	
	"""

	log.info ( "Creating mock_service" )
	mock_service = RedisResolutionService (
		resolver = MockResolver (), config_or_client = redisdb_client
	)
	mock_service.async_timeout = 1.0  # make tests faster
	mock_service.start () # Starts in the background

	log.info ( "mock_service started, handing control to tests" )

	try:
		yield
	finally:
		mock_service.stop ()



@pytest.fixture
def mock_ere_client ( redisdb_client: redis.Redis ) -> AbstractClient:
	return RedisEREClient ( config_or_client = redisdb_client )


@pytest.fixture
def redisdb_client () -> Generator[redis.Redis, None, None]:
	"""
	Provides a Redis client through Test Containers.
	"""
	with RedisContainer() as redis_container:
		yield redis_container.get_client()
