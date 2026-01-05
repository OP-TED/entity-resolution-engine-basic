from ere.models.ers_core import Request, Response


from abc import abstractmethod
from typing import Protocol


class AbstractResolver ( Protocol ):
	"""
	ERE resolver abstraction.

	An ERE resolver deals with the core of the job, ie, it takes requests like 
  :class:`ere.models.ers_core.Request` and computes results for them. 
	
	A resolver doesn't deal with aspects like networking or asynchronous processing, this
	is are concerns for services and entrypoints, which wrap around resolvers.

	As you can see, it makes sense to define resolvers as :class:`Protocol` classes, so that, 
	for instance, even a simple lambda could be uses as a resolver. 
	"""
	
	@abstractmethod
	def process_request ( self, request: Request ) -> Response:
		"""
		Resolves an entity resolution request, returning the corresponding response.

		This only concerns the resolution logic, leaving out aspects like transport or
		asynchronous processing.

		This should take care of wrapping exceptions into ErrorResponse results.
		"""

	def __call__ ( self, request: Request ) -> Response:
		return self.process_request ( request )