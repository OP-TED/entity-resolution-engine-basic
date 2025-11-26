from abc import ABC
from abc import ABC, abstractmethod
from ere.models.ers_core import Request, Response

class AbstractEREClient ( ABC ):
	@abstractmethod
	def push_request ( self, request: Request ):
			"""
			Push a request to the request channel of the ERE system.
			
			See the ERE Contract document for details.
			"""
			pass
	
	@abstractmethod
	def subscribe_responses ( self ) -> Iterable[ Response ]: 
			"""
			Subscibe to the response channel. This is a generator that yields responses as the implementation
			publish them to the response channel.
			"""
			pass
