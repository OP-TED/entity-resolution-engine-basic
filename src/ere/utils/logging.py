"""Logging utilities for ERE."""

import os
import sys

import logging

# Add TRACE level (below DEBUG)
TRACE_LEVEL_NUM = 5
logging.addLevelName(TRACE_LEVEL_NUM, "TRACE")


def _trace(self, message, *args, **kwargs):
    """Log at TRACE level."""
    if self.isEnabledFor(TRACE_LEVEL_NUM):
        self._log(TRACE_LEVEL_NUM, message, args, **kwargs)  # pylint: disable=protected-access


# Add trace method to Logger class
logging.Logger.trace = _trace


def configure_logging(log_level: str = None) -> None:
    """
    Set up logging to stdout with ISO 8601 timestamps.

    Args:
        log_level: Log level name (e.g., 'DEBUG', 'INFO', 'TRACE').
                  If None, reads from LOG_LEVEL environment variable (default: INFO).
    """
    if log_level is None:
        log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    else:
        log_level = log_level.upper()

    # Handle TRACE level
    if log_level == "TRACE":
        level = TRACE_LEVEL_NUM
    else:
        level = getattr(logging, log_level, logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        stream=sys.stdout,
    )
    logging.getLogger(__name__).info("Logging configured at level %s", log_level)
