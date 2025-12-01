import pytest
from assertpy import assert_that
from rdflib import Graph

from ere import AbstractEREClient
from ere.models.ers_core import CanonicalEntity, EntityResolutionRequest, EntityResolution, Entity

from ere_test import MockupEREClient

# TODO: factorise
EPD_NS = "http://data.europa.eu/a4g/resource/"
ORG_NS = "http://www.w3.org/ns/org#"


# TODO: move to a utility module
def catch_entity_resolution ( ere_cli: AbstractEREClient, request_id: str ) -> EntityResolution:
	for response in ere_cli.subscribe_responses ():
		if response.requestId == request_id:
			return response
	raise RuntimeError ( f"No response found for request ID '{request_id}'" )

@pytest.fixture
def mockup_ere_client () -> AbstractEREClient:
	return MockupEREClient ()

# TODO: add Gherkin annotations
def test_known_entity_resolution ( mockup_ere_client: AbstractEREClient ):
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

		ASK WHERE {
			BIND ( <%s> AS ?ent ).
			%s
		}
		"""
		sparql_ask = sparql_ask % ( canonical_entity.id, sparql_assertion )
		print ( f"SPARQL ASK for assertion '{assertion_label}':\n{sparql_ask}" )
		assert_that ( graph.query ( sparql_ask ).askAnswer, assertion_label ).is_true ()
	