import pytest
from assertpy import assert_that
from ere_test import (EPD_NS, EPO_NS, ORG_NS, MockEREClient, catch_response,
                      extract_resource_rdf, prefix_common_namespaces)
from pyparsing import Path
from rdflib import Graph

from ere.models.ers_core import (CanonicalEntity, Entity,
                                 EntityResolutionRequest,
                                 EntityResolutionResponse, ErrorResponse,
                                 RebuildRequest, RebuildResponse)
from ere.service import AbstractEREClient


@pytest.fixture
def mock_ere_client () -> AbstractEREClient:
	return MockEREClient ()

# TODO: add Gherkin annotations
def test_known_entity_resolution ( mock_ere_client: AbstractEREClient ):
	"""
	Scenario: A known entity returns the canonical entity it's equivalent to
	"""
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
	

def test_unknown_entity_resolution ( mock_ere_client: AbstractEREClient ):
	"""
	Scenario: An unknown entity resolves to itself

	An unknown entity, with no equivalents known to ERE results into a new cluster with the
	entity itself as canonical entity.
	"""
	test_entity = Entity (
		id = f"{EPD_NS}id_unknown_entity_001",
		type = f"{ORG_NS}Organization"
	)
	entity_rdf = f"""
		<{test_entity.id}> a <{test_entity.type}> ;
			epo:hasLegalName "Unknown Entity Ltd."@en ;
			epo:hasPrimaryContactPoint [
				cccev:email "unknown@example.com"
			] ;
			cccev:registeredAddress [
				locn:thoroughfare "123 Unknown St." ;
				locn:addressLocality "Unknown City" ;
				locn:postalCode "00000" ;
				locn:addressCountry "Neverland"
			].
	"""

	entity_rdf = prefix_common_namespaces ( entity_rdf )
	test_entity.entityData = entity_rdf
	test_entity.entityDataFormat = "text/turtle"

	test_req = EntityResolutionRequest (
		requestId = "test-unknown-entity-resolution-001",
		entity = test_entity,
		originator = "test-module"
	)

	mock_ere_client.push_request ( test_req )
	entity_resolution = catch_response ( mock_ere_client, test_req.requestId, EntityResolutionResponse )
	assert_that ( entity_resolution.confidenceLevel, "Resolution response has a confidence score of 1" )\
		.is_equal_to ( 1 )
	
	test_graph = Graph ()
	test_graph.parse ( data = test_entity.entityData, format = 'turtle' )

	canonical_entity: CanonicalEntity = entity_resolution.canonicalEntity
	assert_that ( canonical_entity, "We have a canonical entity in the resolution response" )\
		.is_not_none ()
	
	assert_that ( canonical_entity.id, "Canonical entity has the expected URI" ).\
		is_equal_to ( test_entity.id )
	
	# TODO: see above about this
	assert_that ( canonical_entity.entityDataFormat, "Canonical entity has the expected data format" )\
		.is_equal_to ( "text/turtle" )
	
	canonical_graph = Graph ()
	canonical_graph.parse ( data = canonical_entity.entityData, format = 'turtle' )

	assert_that (
		canonical_graph.isomorphic ( test_graph ),
		"Canonical entity data is equivalent to the source entity data"
	).is_true ()


def test_non_matching_entity_resolves_to_itself ( mock_ere_client: AbstractEREClient ):
	"""
	Scenario: An unknown entity without a sufficient similarity to known entities resolves to itself
	"""
	test_entity = Entity (
		id = f"{EPD_NS}id_2023-S-211-665742_Procedure_faF7Q5dyoGpXu3Ru4RGg73",
		type = f"{EPO_NS}Procedure"
	)

	# Load the RDF from the same test file, don't depend on the internal mock store
	graph = Graph ()
	graph.parse ( Path ( __file__ ).parent / 'resources/example-6.ttl', format = 'turtle' )
	entity_graph = extract_resource_rdf ( graph, test_entity.id )
	test_entity.entityData = entity_graph.serialize ( format = 'turtle' )
	test_entity.entityDataFormat = 'text/turtle'

	test_req = EntityResolutionRequest (
		requestId = "test-low-score-entity-resolution-001",
		entity = test_entity,
		originator = "test-module"
	)

	mock_ere_client.push_request ( test_req )
	entity_resolution = catch_response ( mock_ere_client, test_req.requestId, EntityResolutionResponse )

	assert_that ( entity_resolution.sourceEntityId, "Resolution response has the source entity ID" )\
	  .is_equal_to ( test_entity.id )
	assert_that ( entity_resolution.confidenceLevel, "Resolution response has a confidence score of 1" )\
	  .is_equal_to ( 1 )
	
	canonical_entity: CanonicalEntity = entity_resolution.canonicalEntity
	assert_that ( canonical_entity, "We have a canonical entity in the resolution response" )\
		.is_not_none ()
	assert_that ( canonical_entity.id, "Canonical entity has the expected URI" ).\
	  is_equal_to ( test_entity.id )
	assert_that ( canonical_entity.entityDataFormat, "Canonical entity has the expected data format" )\
	  .is_equal_to ( "text/turtle" )
	
	canonical_graph = Graph ()
	canonical_graph.parse ( data = canonical_entity.entityData, format = 'turtle' )
	assert_that (
		canonical_graph.isomorphic ( entity_graph ),
		"Canonical entity data is equivalent to the source entity data"
	).is_true ()


def test_ere_acknowledges_rebuild_request ( mock_ere_client: AbstractEREClient ):
	"""
	Scenario: The ERE acknowledges a rebuild request
	"""
	rebuild_request = RebuildRequest (
		requestId = "test-ere-acknowledges-rebuild-request-001",
		originator = "test-module"
	)

	mock_ere_client.push_request ( rebuild_request )
	# Does all the assertions we want here
	catch_response ( mock_ere_client, rebuild_request.requestId, RebuildResponse )


def test_ere_still_working_after_rebuild ( mock_ere_client: AbstractEREClient ):
	"""
	Scenario: The ERE keeps resolving entities as usually after a rebuild request
	"""
	# First, send a rebuild request
	rebuild_request = RebuildRequest (
		requestId = "test-ere-still-working-after-rebuild-001",
		originator = "test-module"
	)
	mock_ere_client.push_request ( rebuild_request )
	catch_response ( mock_ere_client, rebuild_request.requestId, RebuildResponse )

	# Now just repeat previous tests
	test_known_entity_resolution ( mock_ere_client )
	test_unknown_entity_resolution ( mock_ere_client )
	test_non_matching_entity_resolves_to_itself ( mock_ere_client )


def test_ere_replies_with_error_response_to_malformed_request ( mock_ere_client: AbstractEREClient ):
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

