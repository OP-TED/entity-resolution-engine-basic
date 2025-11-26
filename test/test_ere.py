from assertpy import assert_that

from ere import AbstractEREClient
from ere.models.ers_core import CanonicalEntity, EntityResolutionRequest, EntityResolution, Entity


# TODO: remove when things will be more stable
def test_stub ():
	assert_that ( True, "This is a test stub. True is true :-)" ).is_true ()

# TODO: move to a utility module
def catch_entity_resolution ( ere_cli: AbstractEREClient, request_id: str ) -> EntityResolution:
	for resp in ere_cli.subscribe_responses ():
		if resp.request_id == request_id:
			return resp.entity_resolution
	raise RuntimeError ( f"No response found for request ID '{request_id}'" )

@pytest.fixture
def mockup_ere_client () -> AbstractEREClient:
	pass

# TODO: add Gherking annotations
def test_new_entity_resolution ( mockup_ere_client: AbstractEREClient ):
	test_entity = Entity ()
	# TODO: fill the entity with test data
	test_req = EntityResolutionRequest ()
	test_req.request_id = "test-req-001"
	test_req.entity = test_entity

	mockup_ere_client.push_request ( test_req )
	entity_resolution = catch_entity_resolution ( mockup_ere_client, test_req.request_id )

	assert_that ( entity_resolution, "We have an entity resolution response" ).is_not_none ()
	assert_that ( entity_resolution.sourceEntityId, "Resolution response has the source entity ID" )\
	  .is_equal_to ( test_entity.id )
	
	canonical_entity: CanonicalEntity = entity_resolution.canonicalEntity
	assert_that ( canonical_entity, "We have a canonical entity in the resolution response" )\
		.is_not_none ()

	assert_that ( canonical_entity.entityData, "Canonical entity is == original entity" ).\
	  is_equal_to ( test_entity.entityData )
	
