"""
Abstract definitions for the ERE service
"""


from concurrent.futures import Executor, InterpreterPoolExecutor
import os
from ere.models.ers_core import Request, Response

from abc import ABC, abstractmethod

from typing import Protocol
from collections.abc import Iterable

class AbstractService ( ABC ):
	"""
	In general, an ERE service can be started and stopped, with default implementations
	doing nothing.
	"""
	@abstractmethod
	def start ( self ):
		pass
	
	@abstractmethod
	def stop ( self ):
		pass


class AbstractResolver ( Protocol ):
	@abstractmethod
	def process_request ( self, request: Request ) -> Response:
		"""
		Resolves an entity resolution request, returning the corresponding response.

		This only concerns the resolution logic, leaving out aspects like transport or
		asynchronous processing.

		This should take care of wrapping exceptions into ErrorResponse results.
		"""
		pass

	def __call__ ( self, request: Request ) -> Response:
		return self.process_request ( request )
	

class AbstractPubSubResolutionService ( AbstractService, AbstractResolver ):
	"""
	An abstract ERE resolution service that works in a publish-subscribe fashion.

	This is a skeleton for concrete implementations that base their service on 
	fetching requests from some source (a channel, a message queue, etc) and pushing
	responses to some sink (a channel, a message queue, etc).

	As such, it delegates the actual resolution to an :class:`AbstractResolver`, and
	we wrap it with placeholders and defaults to manage the publish-subscribe cycle
	in asynchronous/parallel fashion. See below for details.

	
	## Attributes

	- resolver: An :class:`AbstractResolver` instance that does the actual resolution work.
	- parallelism: The number of parallel workers to use for processing requests. 
		By default, it uses the number of CPU cores.
	- executor_type: The type of executor to use for parallel processing. By default, it 
		uses :class:`InterpreterPoolExecutor`, which is optimised for CPU-bound tasks, as it is
		expected for the delegate resolver.
	- is_running: A boolean flag indicating whether the service is running.
	  This is read-only and managed by :meth:`_service_loop`, which in turn should be
		launched by :meth:`start`, and by meth:`stop`. 
	"""

	def __init__( self, resolver: AbstractResolver = None ):
		self.resolver: AbstractResolver = resolver
		self.parallelism: int = os.cpu_count ()
		self.executor_type: Executor = InterpreterPoolExecutor
		self.is_running: bool = False


	@abstractmethod
	async def _pull_request ( self ) -> Request:
		"""
		Pulls a request from a request channel or alike resource.

		This is an abstract placeholder to be implemented by concrete subclasses.
		"""
		pass

	@abstractmethod
	def _push_response ( self, response: Response ):
		"""
		Pushes a response to a response channel or alike resource.

		This is an abstract placeholder to be implemented by concrete subclasses.
		"""
		pass


	async def _service_loop ( self ):
		"""
		The service loop. The default implementation keeps pulling requests, sending them
		to the delegate resolver and pushing the responses.

		This is based on:
		- Calling the :meth:`_pull_request` asynchronously
		- Sending requests to the delegate resolver in parallel, using the configured
		  :attr:`executor_type` and :attr:`parallelism`, and :meth:`_process_push_helper`
		- Repeating, while :meth:`_process_push_helper` pushes responses in parallel (see it)

		TODO: The input queue isn't bounded. Usually, this can be set in the implementing
		subsystem (eg, Redis). In future, we may want to add semaphore-based limiting.
		"""
		self.is_running = True
		while self.is_running:
			with self.executor_type ( max_workers = self.parallelism ) as executor:		
				request = await self._pull_request ()
				executor.submit ( self._process_push_helper, request )


	def _process_push_helper ( self, request: Request ):
		"""
		Helper used by :meth:`_service_loop` to submit a request to the delegate resolver
		and push its response to :meth:`_push_response`.

		Since this method is passed to the service's executor, both the two steps above
		are a sequence that is run in parallel, while :meth:`_service_loop` keeps pulling
		requests and dispatching them to this method.
		"""
		response = self.resolver.process_request ( request )
		self._push_response ( response )

# TODO: 
# - Redis impl, Redis client
# - default start/stop?
#

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