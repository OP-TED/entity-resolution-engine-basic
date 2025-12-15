from collections.abc import Iterable
from concurrent.futures import InterpreterPoolExecutor
import json
import logging
import os
import asyncio

import redis
from redis.exceptions import ConnectionError, TimeoutError

from ere.service import AbstractPubSubResolutionService, AbstractResolver, AbstractEREClient
from ere.models.ers_core import ( 
	Request, Response, EntityResolutionRequest, EntityResolution,
	ErrorResponse, RebuildRequest, RebuildResponse, RequestOrResponseMixin
)

from linkml_runtime.loaders import JSONLoader
from linkml_runtime.dumpers import JSONDumper


log = logging.getLogger ( __name__ )

# TODO: open-closed principle. For now, we don't see much need to extend these
#
SUPPORTED_REQUEST_CLASSES = {
	cls.__name__: cls
	for cls in [ EntityResolutionRequest, RebuildRequest ]
}
SUPPORTED_RESPONSE_CLASSES = {
	cls.__name__: cls
	for cls in [ EntityResolution, RebuildResponse, ErrorResponse ]
}

class RedisConnectionConfig:
	"""
	TODO: comment me
	"""

	def __init__ ( self, host: str = 'localhost', port: int = 6379, db: int = 0 ):
		self.host = host
		self.port = port
		self.db = db

	def __str__(self):
		return f"RedisConnectionConfig ( host: \"{self.host}\", port: \"{self.port}\", db: \"{self.db}\" )"


class RedisResolutionService ( AbstractPubSubResolutionService ):
	"""
	An ERE resolution service that uses Redis as the publish-subscribe mechanism.

	This class should implement the methods to fetch requests from a Redis channel
	and push responses to another Redis channel. The actual resolution logic is
	delegated to the provided resolver.
	"""

	def __init__( 
			self,
			resolver: AbstractResolver = None,
			config_or_client: RedisConnectionConfig | redis.Redis = RedisConnectionConfig()
	):
		super().__init__ ( resolver )
		
		if isinstance ( config_or_client, RedisConnectionConfig ):
			self.config = config_or_client
		else:
			self._redis_client = config_or_client

		self.character_encoding = 'utf-8'

		self.request_channel_id = 'ere_requests'
		self.response_channel_id = 'ere_responses'

	
	async def _pull_request ( self ) -> Request:
		_, raw_msg = self._redis_client.brpop ( self.request_channel_id )
		request = get_request ( raw_msg, self.character_encoding )
		log.debug ( f"RedisResolutionService, pulled request id: {request.requestId}" )
		return request
	

	def _push_response ( self, response: Response ):
		log.debug ( f"RedisResolutionService, pushing response id: {response.requestId}" )
		msg_json_str = _linkml_dumper.dumps ( response )		
		self._redis_client.lpush ( self.response_channel_id, msg_json_str )


class RedisEREClient ( AbstractEREClient ):
	"""
	A simple ERE client that interacts with the RedisResolutionService.
	"""
	
	def __init__ ( 
			self,
			config_or_client: RedisConnectionConfig | redis.Redis = RedisConnectionConfig ()
	):
		if isinstance ( config_or_client, RedisConnectionConfig ):
			self.config = config_or_client
			self._redis_client = redis.Redis ( 
				host = self.config.host, port = self.config.port, db = self.config.db
			)
		else:
			self._redis_client = config_or_client

		self.character_encoding = 'utf-8'

		self.request_channel_id = 'ere_requests'
		self.response_channel_id = 'ere_responses'

		
	def push_request ( self, request: Request ):
		log.debug ( f"Redis ERE client, pushing request id: {request.requestId}" )
		msg_json_str = _linkml_dumper.dumps ( request )
		self._redis_client.lpush ( self.request_channel_id, msg_json_str )
		log.debug ( f"Redis ERE client, request id: {request.requestId} sent" )

	
	def subscribe_responses ( self ) -> Iterable[ Response ]:
		while True:
			try:
				_, raw_msg = self._redis_client.brpop ( self.response_channel_id )
				response = get_response ( raw_msg, self.character_encoding )
				log.debug ( f"Redis ERE client, received response id: {response.requestId}" )
				yield response
			except ( ConnectionError, TimeoutError ) as ex:
				log.error ( f"Redis ERE client, ending subscribe_responses() due to connection issue: {ex}" )
				raise


def get_request (
	raw_msg: bytes, 
	character_encoding: str = 'utf-8'
) -> Request :
	return get_message ( raw_msg, SUPPORTED_REQUEST_CLASSES, character_encoding )  

def get_response (
	raw_msg: bytes, 
	character_encoding: str = 'utf-8'
) -> Response :
	return get_message ( raw_msg, SUPPORTED_RESPONSE_CLASSES, character_encoding )


def get_message ( 
	raw_msg: bytes, 
	supported_classes: dict [str, RequestOrResponseMixin],
	character_encoding: str = 'utf-8'
) -> RequestOrResponseMixin:
	msg_str = raw_msg.decode ( character_encoding )
	msg_json = json.loads ( msg_str )
	
	message_type = msg_json.get ( 'type' )
	if not message_type:
		raise ValueError ( "ERE: message without 'type' field" )
	
	cls = supported_classes.get ( message_type )
	if not cls:
		raise ValueError ( f"ERE: unsupported message class: \"{message_type}\"" )
	
	return _linkml_loader.load_any ( 
		source = msg_json, target_class = cls
	)
	
_linkml_loader = JSONLoader ()
_linkml_dumper = JSONDumper ()