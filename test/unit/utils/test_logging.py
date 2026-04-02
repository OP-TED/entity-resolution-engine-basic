"""Unit tests for utils.logging: log-level setup and TRACE level."""

import logging
from unittest.mock import call, patch

import pytest

from ere.utils.logging import TRACE_LEVEL_NUM, configure_logging


def test_configure_logging_passes_warning_level_to_basicconfig():
    with patch("logging.basicConfig") as mock_bc:
        configure_logging("WARNING")
    mock_bc.assert_called_once()
    assert mock_bc.call_args[1]["level"] == logging.WARNING


def test_configure_logging_passes_trace_level_to_basicconfig():
    with patch("logging.basicConfig") as mock_bc:
        configure_logging("TRACE")
    mock_bc.assert_called_once()
    assert mock_bc.call_args[1]["level"] == TRACE_LEVEL_NUM


def test_configure_logging_reads_env_var(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "ERROR")
    with patch("logging.basicConfig") as mock_bc:
        configure_logging()
    assert mock_bc.call_args[1]["level"] == logging.ERROR


def test_configure_logging_defaults_to_info(monkeypatch):
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    with patch("logging.basicConfig") as mock_bc:
        configure_logging()
    assert mock_bc.call_args[1]["level"] == logging.INFO


def test_trace_method_exists_on_logger():
    log = logging.getLogger("test.trace")
    assert callable(getattr(log, "trace", None))


def test_trace_method_logs_when_enabled(caplog):
    log = logging.getLogger("test.trace.enabled")
    with caplog.at_level(TRACE_LEVEL_NUM, logger="test.trace.enabled"):
        log.trace("trace message sent")
    assert "trace message sent" in caplog.text


def test_trace_method_does_not_log_when_disabled():
    log = logging.getLogger("test.trace.silent")
    log.setLevel(logging.INFO)
    log.trace("this should not explode")
