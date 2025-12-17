"""
Tests the :class:`RedisResolutionService` and :class:`RedisEREClient` with the mock resolver.
"""

import logging
import pytest
from ere.service import AbstractEREClient
from ere.service.redis import RedisResolutionService, RedisEREClient
from ere_test import (
	extract_resource_rdf, prefix_common_namespaces, catch_response, MockResolver,
	EPD_NS, EPO_NS, ORG_NS
)


from ere.models.ers_core import (
	CanonicalEntity,
	EntityResolutionRequest,
	EntityResolutionResponse,
	Entity,
	ErrorResponse,
	RebuildRequest,
	RebuildResponse,
	Response
)

from rdflib import Graph

from assertpy import assert_that

import pytest
import asyncio

log = logging.getLogger ( __name__ )


@pytest.fixture ( autouse = True )
def create_mock_service ( redisdb ):
	log.info ( "Creating mock_service" )
	mock_service = RedisResolutionService (
		resolver = MockResolver (), config_or_client = redisdb
	)
	mock_service.async_timeout = 1.0  # make tests faster
	mock_service.start () # Starts in the background

	log.info ( "mock_service started, handing control to tests" )

	try:
		yield
	finally:
		mock_service.stop ()



@pytest.fixture
def mock_ere_client ( redisdb ) -> AbstractEREClient:
	return RedisEREClient ( config_or_client = redisdb )


@pytest.mark.integration
def test_known_entity_resolution ( mock_ere_client: AbstractEREClient ):
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
