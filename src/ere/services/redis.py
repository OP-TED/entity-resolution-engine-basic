import asyncio
import logging

import redis
from linkml_runtime.dumpers import JSONDumper
from erspec.models.ere import ERERequest, EREResponse

from ere.adapters import AbstractResolver
from ere.adapters.utils import get_request_from_message
from ere.adapters.redis import RedisConnectionConfig
from ere.services import AbstractPubSubResolutionService

log = logging.getLogger(__name__)

_linkml_dumper = JSONDumper()  # Just to cache it


class RedisResolutionService(AbstractPubSubResolutionService):
    """
    An ERE resolution service that uses Redis as the publish-subscribe mechanism.

    This class should implement the methods to fetch requests from a Redis channel
    and push responses to another Redis channel. The actual resolution logic is
    delegated to the provided resolver.
    """

    def __init__(
        self,
        resolver: AbstractResolver = None,
        config_or_client: RedisConnectionConfig | redis.Redis = RedisConnectionConfig(),
    ):
        super().__init__(resolver)

        if isinstance(config_or_client, RedisConnectionConfig):
            self.config = config_or_client
            log.info("RedisResolutionService: connecting to %s", self.config)
            self._redis_client = redis.Redis(
                host=self.config.host, port=self.config.port, db=self.config.db
            )
        else:
            log.info(
                "RedisResolutionService: using existing redis client #%s", id(config_or_client)
            )
            conn_args = config_or_client.connection_pool.connection_kwargs
            log.debug(
                "Redis client config: host=%s, port=%s, db=%s, unix_socket_path=%s",
                conn_args.get('host'), conn_args.get('port'), conn_args.get('db'), conn_args.get('unix_socket_path')
            )
            self._redis_client = config_or_client

        self.character_encoding = "utf-8"

        self.request_channel_id = "ere_requests"
        self.response_channel_id = "ere_responses"

    async def _pull_request(self) -> ERERequest:
        log.debug(
            "RedisResolutionService, Pulling request from channel: %s", self.request_channel_id
        )

        loop = asyncio.get_running_loop()
        _, raw_msg = await loop.run_in_executor(
            None,
            lambda: self._redis_client.brpop(
                self.request_channel_id, timeout=self.async_timeout
            ),
        )

        request = get_request_from_message(raw_msg, self.character_encoding)
        log.debug("RedisResolutionService, pulled request id: %s", request.ereRequestId)
        return request

    def _push_response(self, response: EREResponse):
        log.debug(
            "RedisResolutionService, pushing response id: %s to channel: %s", response.ereRequestId, self.response_channel_id
        )
        msg_json_str = _linkml_dumper.dumps(response)
        self._redis_client.lpush(self.response_channel_id, msg_json_str)
        log.debug("RedisResolutionService, response id: %s sent", response.ereRequestId)
