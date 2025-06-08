import logging
from unittest.mock import Mock

import pytest
from pytest_structlog import StructuredLogCapture
import structlog

from prometheus_aioexporter._log import (
    AccessLogger,
    LogFormat,
    LogLevel,
    setup_logging,
)


class TestLogLevel:
    @pytest.mark.parametrize("level", list(LogLevel))
    def test_repr(self, level: LogLevel) -> None:
        assert repr(level) == level.name


class TestSetupLogging:
    @pytest.mark.parametrize("format", [LogFormat.PLAIN, LogFormat.JSON])
    def test_log_context(
        self, log: StructuredLogCapture, format: LogFormat
    ) -> None:
        setup_logging(log_format=format)
        logger = structlog.get_logger()
        logger.info("info event", some="context")
        [event] = log.events
        assert event["level"] == "info"
        assert "timestamp" in event
        assert event["some"] == "context"


class TestAccessLogger:
    def test_log_request(self, log: StructuredLogCapture) -> None:
        logger = AccessLogger(logging.getLogger(), "ignored format")
        request = Mock(method="GET", path="/foo", remote="192.168.1.1")
        response = Mock(status=200, body_length=123)
        duration = 0.1234
        logger.log(request, response, duration)
        assert log.has(
            "request",
            method="GET",
            path="/foo",
            remote="192.168.1.1",
            status=200,
            size=123,
            duration=duration,
            level="debug",
        )
