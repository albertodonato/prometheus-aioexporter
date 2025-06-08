from enum import IntEnum, StrEnum
from functools import cached_property
import logging
import typing as t

from aiohttp.abc import AbstractAccessLogger
from aiohttp.web import BaseRequest, StreamResponse
import structlog


class LogFormat(StrEnum):
    """Log output format."""

    PLAIN = "plain"
    JSON = "json"


class LogLevel(IntEnum):
    """Log output level."""

    CRITICAL = logging.CRITICAL
    ERROR = logging.ERROR
    WARNING = logging.WARNING
    INFO = logging.INFO
    DEBUG = logging.DEBUG

    def __repr__(self) -> str:
        return self.name


class AccessLogger(AbstractAccessLogger):
    """Access logger for aiohttp."""

    @cached_property
    def _logger(self) -> structlog.stdlib.BoundLogger:
        return t.cast(structlog.stdlib.BoundLogger, structlog.get_logger())

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
            structlog.processors.ExceptionRenderer(
                structlog.tracebacks.ExceptionDictTransformer(
                    show_locals=False
                )
            ),
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
    )
