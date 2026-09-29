"""Redis connection configuration and factory for the ERE service."""

import logging
import os
from dataclasses import dataclass

import redis

log = logging.getLogger(__name__)


@dataclass
class RedisConnectionConfig:
    """Holds Redis connection parameters and creates the sync client."""

    host: str
    port: int
    db: int
    password: str | None = None
    tls: bool = False

    @classmethod
    def from_env(cls) -> "RedisConnectionConfig":
        """Build config from environment variables.

        Reads REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD, REDIS_TLS.
        All have sensible defaults so the service starts without any configuration.

        Returns:
            RedisConnectionConfig populated from the environment.
        """
        return cls(
            host=os.environ.get("REDIS_HOST", "localhost"),
            port=int(os.environ.get("REDIS_PORT", "6379")),
            db=int(os.environ.get("REDIS_DB", "0")),
            password=os.environ.get("REDIS_PASSWORD"),
            tls=os.environ.get("REDIS_TLS", "false").lower() == "true",
        )

    def create_client(self) -> redis.Redis:
        """Create and return a sync Redis client for this configuration.

        Returns:
            A redis.Redis instance ready for use.
        """
        log.info(
            "Connecting to Redis: host=%s, port=%d, db=%d, tls=%s",
            self.host,
            self.port,
            self.db,
            self.tls,
        )
        return redis.Redis(
            host=self.host,
            port=self.port,
            db=self.db,
            password=self.password,
            ssl=self.tls,
            decode_responses=False,
        )

    def __str__(self) -> str:
        return (
            f'RedisConnectionConfig ( host: "{self.host}", port: "{self.port}", db: "{self.db}", tls: "{self.tls}" )'
        )
