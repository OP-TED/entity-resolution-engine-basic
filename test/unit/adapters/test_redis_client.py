"""Unit tests for ere.adapters.redis_client.RedisConnectionConfig."""

from unittest.mock import MagicMock, patch

import pytest

from ere.adapters.redis_client import RedisConnectionConfig


class TestFromEnvDefaults:
    def test_defaults_when_no_env_vars(self, monkeypatch):
        for key in ("REDIS_HOST", "REDIS_PORT", "REDIS_DB", "REDIS_PASSWORD", "REDIS_TLS"):
            monkeypatch.delenv(key, raising=False)

        cfg = RedisConnectionConfig.from_env()

        assert cfg.host == "localhost"
        assert cfg.port == 6379
        assert cfg.db == 0
        assert cfg.password is None
        assert cfg.tls is False

    def test_reads_redis_tls_true(self, monkeypatch):
        monkeypatch.setenv("REDIS_TLS", "true")

        cfg = RedisConnectionConfig.from_env()

        assert cfg.tls is True

    def test_reads_redis_tls_case_insensitive(self, monkeypatch):
        monkeypatch.setenv("REDIS_TLS", "True")

        cfg = RedisConnectionConfig.from_env()

        assert cfg.tls is True

    def test_reads_host_port_db(self, monkeypatch):
        monkeypatch.setenv("REDIS_HOST", "redis.example.com")
        monkeypatch.setenv("REDIS_PORT", "6380")
        monkeypatch.setenv("REDIS_DB", "2")

        cfg = RedisConnectionConfig.from_env()

        assert cfg.host == "redis.example.com"
        assert cfg.port == 6380
        assert cfg.db == 2


class TestCreateClient:
    def test_ssl_false_by_default(self, monkeypatch):
        monkeypatch.delenv("REDIS_TLS", raising=False)
        cfg = RedisConnectionConfig.from_env()

        with patch("ere.adapters.redis_client.redis.Redis") as mock_redis_cls:
            mock_redis_cls.return_value = MagicMock()
            cfg.create_client()

        _, kwargs = mock_redis_cls.call_args
        assert kwargs["ssl"] is False

    def test_ssl_true_when_tls_enabled(self, monkeypatch):
        monkeypatch.setenv("REDIS_TLS", "true")
        cfg = RedisConnectionConfig.from_env()

        with patch("ere.adapters.redis_client.redis.Redis") as mock_redis_cls:
            mock_redis_cls.return_value = MagicMock()
            cfg.create_client()

        _, kwargs = mock_redis_cls.call_args
        assert kwargs["ssl"] is True

    def test_decode_responses_is_false(self, monkeypatch):
        monkeypatch.delenv("REDIS_TLS", raising=False)
        cfg = RedisConnectionConfig.from_env()

        with patch("ere.adapters.redis_client.redis.Redis") as mock_redis_cls:
            mock_redis_cls.return_value = MagicMock()
            cfg.create_client()

        _, kwargs = mock_redis_cls.call_args
        assert kwargs["decode_responses"] is False