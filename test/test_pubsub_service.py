"""
Tests the generic working logic in :class:`AbstractPubSubResolutionService`, 

by means of mock implementations that use 'channels' based on in-memory queues.
"""

import asyncio
import logging
import queue
from collections.abc import Iterable

import pytest
from assertpy import assert_that
from ere_test import EPD_NS, ORG_NS, MockResolver, catch_response

from ere.models.ers_core import (Entity, EntityResolutionRequest,
                                 EntityResolutionResponse, Request, Response)
from ere.service import AbstractEREClient, AbstractPubSubResolutionService

log = logging.getLogger ( __name__ )


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


@pytest.fixture
def mock_ere_client () -> AbstractEREClient:
	return FooPubSubClient ()


@pytest.fixture ( autouse = True )
def create_mock_service ():
	"""
	The service fixture isn't directly used by the tests, for they interact with the client fixture 
	through network communication, or mechanisms that emulate it (like in-memory queues used hereby).
	
	"""
	log.info ( "Creating mock_service" )
	mock_service = FooPubSubResolutionService ()
	mock_service.async_timeout = 1.0  # make tests faster

	mock_service.start () # Starts in the background

	log.info ( "mock_service started, handing control to tests" )

	try:
		yield
	finally:
		mock_service.stop ()


# The "channels" used by the mock service/client to emulate the interaction in a real service
# implemented with Redis queues, or similar.
#
_request_queue = queue.Queue ()
_response_queue = queue.Queue ()

class FooPubSubResolutionService ( AbstractPubSubResolutionService ):
	"""
	A mock PubSubResolutionService that uses in-memory queues to emulate a real
	message queue service.
	"""
	def __init__ ( self ):
		super ().__init__ ( resolver = MockResolver () )

	async def _pull_request ( self ) -> Request:
		def guarded_get () -> Request | None:
			"""
			Pulls a request from the requst 'channel', enforcing a timeout and managing 
			exceptions like timeout, empty queue, etc.
			"""
			try:
				return _request_queue.get ( timeout = self.async_timeout / 2 )
			except queue.Empty, queue.ShutDown:
				return None
			
		log.debug ( "Service: pulling request from queue" )
		# Needs to go in a thread, in order to not block the event loop in waiting
		request = await asyncio.to_thread( guarded_get )
		id = request.requestId if request else 'None'
		log.debug ( f"Service: got a request from queue, id: {id}" )

		return request
	
	def _push_response ( self, response: Response ):
		log.debug ( f"Service: pushing response to queue, id: {response.requestId}" )
		_response_queue.put_nowait ( response )
		log.debug ( f"Service: pushed response to queue, id: {response.requestId}" )


class FooPubSubClient ( AbstractEREClient ):
	"""
	The counterpart of :class:`FooPubSubResolutionService`

	Uses the in-memory queues to emulate a client interacting with an ERE service through
	a message queue service.
	"""
	def push_request ( self, request: Request ):
		log.debug ( f"Client: pushing request to queue, id: {request.requestId}" )
		_request_queue.put_nowait ( request )
		log.debug ( f"Client: pushed request to queue, id: {request.requestId}" )
	
	def subscribe_responses ( self ) -> Iterable[ Response ]:
		while True:
			log.debug ( "Client: waiting for response from queue" )
			response = _response_queue.get()
			log.debug ( f"Client: got a response from queue, id: {response.requestId}" )
			yield response

