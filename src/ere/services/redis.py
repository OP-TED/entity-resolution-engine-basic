import asyncio
import json
import logging
from collections.abc import Iterable

import redis
from linkml_runtime.dumpers import JSONDumper
from linkml_runtime.loaders import JSONLoader
from redis.exceptions import ConnectionError, TimeoutError

from ere.models.ers_core import (EntityResolutionRequest,
                                 EntityResolutionResponse, ErrorResponse,
                                 RebuildRequest, RebuildResponse, Request,
                                 RequestOrResponseMixin, Response)
from ere.services import (AbstractEREClient, AbstractPubSubResolutionService,
                         AbstractResolver)

log = logging.getLogger ( __name__ )

# These are used by get_message_object() to map 'type' fields in JSON representations to
# domain model (LinkML) classes.
#
# TODO: open-closed principle. For now, we don't see much need to extend these
# TODO: move to a utils module
#
SUPPORTED_REQUEST_CLASSES = {
	cls.__name__: cls
	for cls in [ EntityResolutionRequest, RebuildRequest ]
}
SUPPORTED_RESPONSE_CLASSES = {
	cls.__name__: cls
	for cls in [ EntityResolutionResponse, RebuildResponse, ErrorResponse ]
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
			config_or_client: RedisConnectionConfig | redis.Redis = RedisConnectionConfig ()
	):
		super().__init__ ( resolver )
		
		if isinstance ( config_or_client, RedisConnectionConfig ):
			self.config = config_or_client
			log.info (f"RedisResolutionService: connecting to {self.config}" )
			self._redis_client = redis.Redis ( 
				host = self.config.host, port = self.config.port, db = self.config.db
			)			
		else:
			log.info ( f"RedisResolutionService: using existing redis client #{id(config_or_client)}" )
			conn_args = config_or_client.connection_pool.connection_kwargs
			log.debug (f"Redis client config: host={conn_args.get('host')}, port={conn_args.get('port')}, db={conn_args.get('db')}, unix_socket_path={conn_args.get('unix_socket_path')}")
			self._redis_client = config_or_client


		self.character_encoding = 'utf-8'

		self.request_channel_id = 'ere_requests'
		self.response_channel_id = 'ere_responses'

	
	async def _pull_request ( self ) -> Request:
		log.debug ( f"RedisResolutionService, Pulling request from channel: {self.request_channel_id}" )
		
		# _, raw_msg = self._redis_client.brpop ( self.request_channel_id )
		loop = asyncio.get_running_loop()
		_, raw_msg = await loop.run_in_executor (
			None,
			lambda: self._redis_client.brpop ( self.request_channel_id, timeout = self.async_timeout )
    )

		request = get_request_from_message ( raw_msg, self.character_encoding )
		log.debug ( f"RedisResolutionService, pulled request id: {request.requestId}" )
		return request
	

	def _push_response ( self, response: Response ):
		log.debug ( f"RedisResolutionService, pushing response id: {response.requestId} to channel: {self.response_channel_id}" )
		msg_json_str = _linkml_dumper.dumps ( response )		
		self._redis_client.lpush ( self.response_channel_id, msg_json_str )
		log.debug ( f"RedisResolutionService, response id: {response.requestId} sent" )


class RedisEREClient ( AbstractEREClient ):
	"""
	A simple ERE client that interacts with a RedisResolutionService.
	"""
	
	def __init__ ( 
			self,
			config_or_client: RedisConnectionConfig | redis.Redis = RedisConnectionConfig ()
	):
		if isinstance ( config_or_client, RedisConnectionConfig ):
			self.config = config_or_client
			log.info (f"RedisEREClient: connecting to {self.config}" )
			self._redis_client = redis.Redis ( 
				host = self.config.host, port = self.config.port, db = self.config.db
			)
		else:
			log.info ( f"RedisEREClient: using existing redis client #{id(config_or_client)}" )
			conn_args = config_or_client.connection_pool.connection_kwargs
			log.debug (f"Redis client config: host={conn_args.get('host')}, port={conn_args.get('port')}, db={conn_args.get('db')}, unix_socket_path={conn_args.get('unix_socket_path')}")
			self._redis_client = config_or_client

		self.character_encoding = 'utf-8'

		self.request_channel_id = 'ere_requests'
		self.response_channel_id = 'ere_responses'

		
	def push_request ( self, request: Request ):
		log.debug ( f"Redis ERE client, pushing request id: {request.requestId} to channel: {self.request_channel_id}" )
		msg_json_str = _linkml_dumper.dumps ( request )
		self._redis_client.lpush ( self.request_channel_id, msg_json_str )
		log.debug ( f"Redis ERE client, request id: {request.requestId} sent" )

	
	def subscribe_responses ( self ) -> Iterable[ Response ]:
		while True:
			try:
				log.debug ( f"Redis ERE client, waiting for response on channel: {self.response_channel_id}" )
				_, raw_msg = self._redis_client.brpop ( self.response_channel_id )
				response = get_response_from_message ( raw_msg, self.character_encoding )
				log.debug ( f"Redis ERE client, received response id: {response.requestId}" )
				yield response
			except ( ConnectionError, TimeoutError ) as ex:
				log.error ( f"Redis ERE client, ending subscribe_responses() due to connection issue: {ex}" )
				raise


def get_request_from_message (
	raw_msg: bytes, 
	character_encoding: str = 'utf-8'
) -> Request :
	"""
	Helper to parse a raw message (bytes) coming from places like a Redis queue into a Request object.

	This is a simple wrapper around :meth:`get_message_object`.
	
	TODO: move to a utils module
	"""
	return get_message_object ( raw_msg, SUPPORTED_REQUEST_CLASSES, character_encoding )  

def get_response_from_message (
	raw_msg: bytes, 
	character_encoding: str = 'utf-8'
) -> Response :
	"""
	Helper to parse a raw message (bytes) coming from places like a Redis queue into a Response object.

	This is a simple wrapper around :meth:`get_message_object`.
	
	TODO: move to a utils module
	"""	
	return get_message_object ( raw_msg, SUPPORTED_RESPONSE_CLASSES, character_encoding )


def get_message_object ( 
	raw_msg: bytes, 
	supported_classes: dict [str, RequestOrResponseMixin],
	character_encoding: str = 'utf-8'
) -> RequestOrResponseMixin:
	"""
	Helper to parse a raw message (bytes) coming from places like a Redis queue into a Request/Response object.

	This parses the initial input into JSON, then it uses the LinkML facilities to create domain model
	instances from the JSON. This requires the :param:`supported_classes` dict to map the 'type' field
	in the JSON to the corresponding class.
	
	TODO: move to a utils module
	"""
	
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