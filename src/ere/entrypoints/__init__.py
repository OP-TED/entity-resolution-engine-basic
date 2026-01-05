from ere.models.ers_core import Request, Response


from abc import ABC, abstractmethod
from collections.abc import Iterable


class AbstractClient ( ABC ):
	"""
	Abstraction of a client to access with an ERE instance.
	"""

	@abstractmethod
	def push_request ( self, request: Request ):
		"""
		Pushes a request to the request channel of the ERE system.

		See the ERE Contract document for details.
		"""

	@abstractmethod
	def subscribe_responses ( self ) -> Iterable[ Response ]:
		"""
		Subscribes to the response channel.

		This is a generator that yields responses as the implementation publishes them 
		to the response channel.
		"""