from abc import ABC
from abc import ABC, abstractmethod
from ere.models.ers_core import Request, Response

class AbstractEREClient ( ABC ):
	@abstractmethod
	def push_request ( self, request: Request ):
			"""
			Pushes a request to the request channel of the ERE system.
			
			See the ERE Contract document for details.
			"""
			pass
	
	@abstractmethod
	def subscribe_responses ( self ) -> Iterable[ Response ]: 
			"""
			Subscribes to the response channel.
			
			This is a generator that yields responses as the implementation publishes them 
			to the response channel.
			"""
			pass
