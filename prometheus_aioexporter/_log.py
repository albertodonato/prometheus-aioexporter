from enum import StrEnum
from functools import cached_property
import logging
from typing import cast

from aiohttp.abc import AbstractAccessLogger
from aiohttp.web import BaseRequest, StreamResponse
import structlog


class LogFormat(StrEnum):
    """Log output format."""

    PLAIN = "plain"
    JSON = "json"

    def __repr__(self) -> str:
        return self.value


class LogLevel(StrEnum):
    """Log output level."""

    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    DEBUG = "debug"

    def num_level(self) -> int:
        """Return the numeric level."""
        return cast(int, getattr(logging, self.name))

    def __repr__(self) -> str:
        return self.value


class AccessLogger(AbstractAccessLogger):
    """Access logger for aiohttp."""

    @cached_property
    def _logger(self) -> structlog.BoundLogger:
        return cast(structlog.BoundLogger, structlog.get_logger())

    def log(
        self, request: BaseRequest, response: StreamResponse, time: float
    ) -> None:
        self._logger.debug(
            "request",
            method=request.method,
            path=request.path,
            remote=request.remote,
            status=response.status,
            size=response.body_length,
            duration=time,
        )


def setup_logging(
    log_format: LogFormat = LogFormat.PLAIN,
    log_level: LogLevel = LogLevel.WARNING,
) -> None:
    """Setup logging for the application."""

    config = structlog.get_config()
    processors = config["processors"]
    if log_format == LogFormat.JSON:
        processors = [
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            log_level.num_level()
        ),
    )
