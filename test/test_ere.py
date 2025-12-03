import pytest
from assertpy import assert_that
from rdflib import Graph

from ere import AbstractEREClient
from ere.models.ers_core import CanonicalEntity, EntityResolutionRequest, EntityResolution, Entity

from ere_test import MockupEREClient

# TODO: factorise
EPD_NS = "http://data.europa.eu/a4g/resource/"
ORG_NS = "http://www.w3.org/ns/org#"


@pytest.fixture
def mockup_ere_client () -> AbstractEREClient:
	return MockupEREClient ()

# TODO: add Gherkin annotations
def test_known_entity_resolution ( mockup_ere_client: AbstractEREClient ):
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

	mockup_ere_client.push_request ( test_req )
	entity_resolution = catch_entity_resolution ( mockup_ere_client, test_req.requestId )

	assert_that ( entity_resolution, "We have an entity resolution response" ).is_not_none ()
	assert_that ( entity_resolution.sourceEntityId, "Resolution response has the source entity ID" )\
	  .is_equal_to ( test_entity.id )
	
	assert_that ( entity_resolution.requestId, "Resolution response has the request ID" ).is_equal_to ( test_req.requestId )
	assert_that ( entity_resolution.confidenceLevel, "Resolution response has a confidence score" )\
	  .is_equal_to ( 0.98 )	

	canonical_entity: CanonicalEntity = entity_resolution.canonicalEntity
	assert_that ( canonical_entity, "We have a canonical entity in the resolution response" )\
		.is_not_none ()

	assert_that ( canonical_entity.id, "Canonical entity has the expected URI" ).\
	  is_equal_to ( f"{EPD_NS}id_2023-S-210-662860_ReviewerOrganisation_LLhJHMi9mby8ixbkfyGoWj" )
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
	
def test_unknown_entity_resolution ( mockup_ere_client: AbstractEREClient ):
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

	mockup_ere_client.push_request ( test_req )
	entity_resolution = catch_entity_resolution ( mockup_ere_client, test_req.requestId )
	assert_that ( entity_resolution, "We have an entity resolution response" ).is_not_none ()
	assert_that ( entity_resolution.sourceEntityId, "Resolution response has the source entity ID" )\
		.is_equal_to ( test_entity.id )
	assert_that ( entity_resolution.confidenceLevel, "Resolution response has a confidence score of 1" )\
		.is_equal_to ( 1 )
	
	test_graph = Graph ()
	test_graph.parse ( data = test_entity.entityData, format = 'turtle' )

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
		canonical_graph.isomorphic ( test_graph ),
		"Canonical entity data is equivalent to the source entity data"
	).is_true ()


# TODO: move to a utility module
def catch_entity_resolution ( ere_cli: AbstractEREClient, request_id: str ) -> EntityResolution:
	"""
	Subscribes to to ERE responses and keeps getting responses until one with the given
	request ID is found.

	If the response flow stops (eg, channel closed, system went down), raises a :class:`RuntimeError`.
	"""
	for response in ere_cli.subscribe_responses ():
		if response.requestId == request_id:
			return response
	raise RuntimeError ( f"No response found for request ID '{request_id}'" )

def prefix_common_namespaces ( rdf_or_sparql_body: str ) -> str:
	"""
	Simple helper to have your Turtle or SPARQL string prefixed with common namespace prefixes.
	"""
	return """
		PREFIX cccev: <http://data.europa.eu/m8g/>
		PREFIX dct:   <http://purl.org/dc/terms/>
		PREFIX ep:    <http://eprints.org/ontology/>
		PREFIX epd:   <http://data.europa.eu/a4g/resource/>
		PREFIX epo:   <http://data.europa.eu/a4g/ontology#>
		PREFIX locn:  <http://www.w3.org/ns/locn#>
		PREFIX org:   <http://www.w3.org/ns/org#>
		PREFIX owl:   <http://www.w3.org/2002/07/owl#>
		PREFIX ql:    <http://semweb.mmlab.be/ns/ql#>
		PREFIX rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
		PREFIX rdfs:  <http://www.w3.org/2000/01/rdf-schema#>
		PREFIX rml:   <http://semweb.mmlab.be/ns/rml#>
		PREFIX rr:    <http://www.w3.org/ns/r2rml#>
		PREFIX skos:  <http://www.w3.org/2004/02/skos/core#>
		PREFIX tedm:  <http://data.europa.eu/a4g/mapping/sf-rml/>
		PREFIX time:  <http://www.w3.org/2006/time#>
		PREFIX xsd:   <http://www.w3.org/2001/XMLSchema#>

	""" + rdf_or_sparql_body