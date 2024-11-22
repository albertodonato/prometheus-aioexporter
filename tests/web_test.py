from collections.abc import (
    Awaitable,
    Callable,
    Coroutine,
    Iterator,
)
from ssl import SSLContext
import typing as t
from unittest import mock

from aiohttp.test_utils import (
    TestClient,
    TestServer,
)
from aiohttp.web import Application, Request
from prometheus_client import Gauge
from prometheus_client.metrics import MetricWrapperBase
import pytest
from pytest_mock import MockerFixture
from pytest_structlog import StructuredLogCapture

from prometheus_aioexporter._log import AccessLogger
from prometheus_aioexporter._metric import (
    MetricConfig,
    MetricsRegistry,
)
from prometheus_aioexporter._web import PrometheusExporter

from .conftest import ssl_context

AiohttpClient = Callable[
    [Application | TestServer], Awaitable[TestClient[Request, Application]]
]
AiohttpServer = Callable[..., Awaitable[TestServer]]


@pytest.fixture
def registry() -> Iterator[MetricsRegistry]:
    yield MetricsRegistry()


@pytest.fixture
def exporter(
    registry: MetricsRegistry, request: pytest.FixtureRequest
) -> Iterator[PrometheusExporter]:
    yield PrometheusExporter(
        name="test-app",
        description="A test application",
        hosts=["localhost"],
        port=8000,
        registry=registry,
        ssl_context=getattr(request, "param", None),
    )


@pytest.fixture
def create_server_client(
    ssl_context: SSLContext,
    aiohttp_server: AiohttpServer,
) -> Iterator[
    Callable[[PrometheusExporter], Coroutine[t.Any, t.Any, TestServer]]
]:
    async def create(exporter: PrometheusExporter) -> TestServer:
        kwargs: dict[str, t.Any] = {}
        if exporter.ssl_context is None:
            kwargs["ssl"] = exporter.ssl_context
        return await aiohttp_server(exporter.app, **kwargs)

    yield create


@pytest.mark.usefixtures("log")
class TestPrometheusExporter:
    def test_app_exporter_reference(
        self, exporter: PrometheusExporter
    ) -> None:
        assert exporter.app["exporter"] is exporter

    @pytest.mark.parametrize("exporter", [ssl_context, None], indirect=True)
    def test_run(
        self, mocker: MockerFixture, exporter: PrometheusExporter
    ) -> None:
        mock_run_app = mocker.patch("prometheus_aioexporter._web.run_app")
        exporter.run()
        mock_run_app.assert_called_with(
            mock.ANY,
            host=["localhost"],
            port=8000,
            print=mock.ANY,
            access_log_class=AccessLogger,
            ssl_context=exporter.ssl_context,
        )

    @pytest.mark.parametrize("exporter", [ssl_context, False], indirect=True)
    async def test_homepage(
        self,
        ssl_context_server: SSLContext | bool,
        create_server_client: Callable[
            [PrometheusExporter], Coroutine[t.Any, t.Any, TestServer]
        ],
        exporter: PrometheusExporter,
        aiohttp_client: AiohttpClient,
    ) -> None:
        server = await create_server_client(exporter)
        client = await aiohttp_client(server)
        ssl_client_context: SSLContext | bool = False
        if exporter.ssl_context is not None:
            ssl_client_context = ssl_context_server
        request = await client.request("GET", "/", ssl=ssl_client_context)
        assert request.status == 200
        assert request.content_type == "text/html"
        text = await request.text()
        assert "<title>test-app - A test application</title>" in text

    async def test_homepage_no_description(
        self,
        aiohttp_client: AiohttpClient,
        exporter: PrometheusExporter,
    ) -> None:
        exporter.description = ""
        client = await aiohttp_client(exporter.app)
        request = await client.request("GET", "/")
        assert request.status == 200
        assert request.content_type == "text/html"
        text = await request.text()
        assert "<title>test-app</title>" in text

    async def test_metrics(
        self,
        aiohttp_client: AiohttpClient,
        exporter: PrometheusExporter,
        registry: MetricsRegistry,
    ) -> None:
        metrics = registry.create_metrics(
            [MetricConfig("test_gauge", "A test gauge", "gauge")]
        )
        gauge = t.cast(Gauge, metrics["test_gauge"])
        gauge.set(12.3)
        client = await aiohttp_client(exporter.app)
        request = await client.request("GET", "/metrics")
        assert request.status == 200
        assert request.content_type == "text/plain"
        text = await request.text()
        assert "HELP test_gauge A test gauge" in text
        assert "test_gauge 12.3" in text

    async def test_metrics_different_path(
        self,
        aiohttp_client: AiohttpClient,
        registry: MetricsRegistry,
        ssl_context: SSLContext,
    ) -> None:
        exporter = PrometheusExporter(
            name="test-app",
            description="A test application",
            hosts=["localhost"],
            port=8000,
            registry=registry,
            metrics_path="/other-path",
            ssl_context=ssl_context,
        )
        metrics = registry.create_metrics(
            [MetricConfig("test_gauge", "A test gauge", "gauge")]
        )
        gaute = t.cast(Gauge, metrics["test_gauge"])
        gaute.set(12.3)
        client = await aiohttp_client(exporter.app)
        request = await client.request("GET", "/other-path")
        assert request.status == 200
        assert request.content_type == "text/plain"
        text = await request.text()
        assert "HELP test_gauge A test gauge" in text
        assert "test_gauge 12.3" in text
        # the /metrics path doesn't exist
        request = await client.request("GET", "/metrics")
        assert request.status == 404

    async def test_metrics_update_handler(
        self,
        aiohttp_client: AiohttpClient,
        exporter: PrometheusExporter,
        registry: MetricsRegistry,
    ) -> None:
        args = []

        async def update_handler(
            metrics: dict[str, MetricWrapperBase],
        ) -> None:
            args.append(metrics)

        exporter.set_metric_update_handler(update_handler)
        metrics = registry.create_metrics(
            [
                MetricConfig("metric1", "A test gauge", "gauge"),
                MetricConfig("metric2", "A test histogram", "histogram"),
            ]
        )
        client = await aiohttp_client(exporter.app)
        await client.request("GET", "/metrics")
        assert args == [metrics]

    @pytest.mark.parametrize(
        ["ssl_context", "protocol"], [(ssl_context, "https"), (None, "http")]
    )
    async def test_startup_logger(
        self,
        log: StructuredLogCapture,
        registry: MetricsRegistry,
        ssl_context: SSLContext,
        protocol: str,
    ) -> None:
        exporter = PrometheusExporter(
            "test-app",
            "A test application",
            ["0.0.0.0", "::1"],
            8000,
            registry,
            ssl_context=ssl_context,
        )
        await exporter._log_startup_message(exporter.app)
        assert log.has(
            "listening", url=f"{protocol}://0.0.0.0:8000", level="info"
        )
        assert log.has(
            "listening", url=f"{protocol}://[::1]:8000", level="info"
        )
