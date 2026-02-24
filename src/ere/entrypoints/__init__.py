from abc import ABC, abstractmethod
from collections.abc import Generator, Iterable

from erspec.models.ere import ERERequest, EREResponse


class AbstractClient(ABC):
    """
    Abstraction of a client to access with an ERE instance.
    """

    @abstractmethod
    def push_request(self, request: ERERequest):
        """
        Pushes a request to the request channel of the ERE system.

        See the ERE Contract document for details.
        """

    @abstractmethod
    def subscribe_responses(self) -> Generator[EREResponse, None, None]:
        """
        Subscribes to the response channel.

        This is a generator that yields responses as the implementation publishes them
        to the response channel.
        """
