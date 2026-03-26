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
from prometheus_aioexporter._web import (
    EXPORTER_APP_KEY,
    PrometheusExporter,
    PrometheusExporterConfig,
)

from .conftest import ssl_context

AiohttpTestClient = TestClient[Request, Application]
AiohttpClientFixture = Callable[
    [Application | TestServer], Awaitable[AiohttpTestClient]
]
AiohttpServerFixture = Callable[..., Awaitable[TestServer]]
CreateExporterClient = Callable[
    [PrometheusExporter], Coroutine[t.Any, t.Any, AiohttpTestClient]
]


@pytest.fixture
def registry() -> Iterator[MetricsRegistry]:
    yield MetricsRegistry()


@pytest.fixture
def config(
    request: pytest.FixtureRequest,
) -> Iterator[PrometheusExporterConfig]:
    yield PrometheusExporterConfig(
        "test-exporter",
        "1.2.3",
        "A test exporter",
        ["localhost"],
        8000,
        ssl_context=getattr(request, "param", None),
    )


@pytest.fixture
def exporter(
    registry: MetricsRegistry,
    config: PrometheusExporterConfig,
) -> Iterator[PrometheusExporter]:
    yield PrometheusExporter(config, registry)


@pytest.fixture
def create_exporter_client(
    ssl_context: SSLContext,
    aiohttp_server: AiohttpServerFixture,
    aiohttp_client: AiohttpClientFixture,
) -> Iterator[CreateExporterClient]:
    async def create(
        exporter: PrometheusExporter,
    ) -> TestClient[Request, Application]:
        kwargs: dict[str, t.Any] = {}
        if exporter.config.ssl_context is None:
            kwargs["ssl"] = exporter.config.ssl_context
        server = await aiohttp_server(exporter.app, **kwargs)
        return await aiohttp_client(server)

    yield create


class TestPrometheusExporterConfig:
    def test_server_version(self, config: PrometheusExporterConfig) -> None:
        assert config.server_version == "test-exporter/1.2.3"


@pytest.mark.usefixtures("log")
class TestPrometheusExporter:
    def test_app_exporter_reference(
        self, exporter: PrometheusExporter
    ) -> None:
        assert exporter.app[EXPORTER_APP_KEY] is exporter

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
            ssl_context=exporter.config.ssl_context,
        )

    @pytest.mark.parametrize("exporter", [ssl_context, False], indirect=True)
    async def test_homepage(
        self,
        ssl_context_server: SSLContext | bool,
        exporter: PrometheusExporter,
        create_exporter_client: CreateExporterClient,
    ) -> None:
        client = await create_exporter_client(exporter)
        response = await client.request("GET", "/", ssl=ssl_context_server)
        assert response.status == 200
        assert response.content_type == "text/html"
        text = await response.text()
        assert "<title>test-exporter</title>" in text
        assert "A test exporter" in text

    async def test_server_version(
        self,
        exporter: PrometheusExporter,
        create_exporter_client: CreateExporterClient,
    ) -> None:
        client = await create_exporter_client(exporter)
        response = await client.request("GET", "/")
        assert response.headers["Server"] == "test-exporter/1.2.3"

    @pytest.mark.parametrize(
        "accept_header,content_type",
        [
            (
                "text/plain;version=0.0.4",
                "text/plain; version=0.0.4; charset=utf-8",
            ),
            (
                "application/openmetrics-text;version=1.0.0",
                "application/openmetrics-text; version=1.0.0; charset=utf-8; escaping=underscores",
            ),
            ("", "text/plain; version=0.0.4; charset=utf-8"),
        ],
    )
    async def test_metrics(
        self,
        aiohttp_client: AiohttpClientFixture,
        exporter: PrometheusExporter,
        registry: MetricsRegistry,
        accept_header: str,
        content_type: str,
    ) -> None:
        metrics = registry.create_metrics(
            [MetricConfig("test_gauge", "A test gauge", "gauge")]
        )
        gauge = t.cast(Gauge, metrics["test_gauge"])
        gauge.set(12.3)
        client = await aiohttp_client(exporter.app)
        response = await client.request(
            "GET", "/metrics", headers={"Accept": accept_header}
        )
        assert response.status == 200
        assert response.headers["Content-Type"] == content_type
        text = await response.text()
        assert "HELP test_gauge A test gauge" in text
        assert "test_gauge 12.3" in text

    async def test_metrics_different_path(
        self,
        aiohttp_client: AiohttpClientFixture,
        registry: MetricsRegistry,
    ) -> None:
        config = PrometheusExporterConfig(
            "test-exportere",
            "1.2.3",
            "A test exporter",
            ["localhost"],
            8000,
            metrics_path="/other-path",
        )
        exporter = PrometheusExporter(config, registry)

        metrics = registry.create_metrics(
            [MetricConfig("test_gauge", "A test gauge", "gauge")]
        )
        gaute = t.cast(Gauge, metrics["test_gauge"])
        gaute.set(12.3)
        client = await aiohttp_client(exporter.app)
        response = await client.request("GET", "/other-path")
        assert response.status == 200
        assert response.content_type == "text/plain"
        text = await response.text()
        assert "HELP test_gauge A test gauge" in text
        assert "test_gauge 12.3" in text
        # the /metrics path doesn't exist
        response = await client.request("GET", "/metrics")
        assert response.status == 404

    async def test_metrics_update_handler(
        self,
        aiohttp_client: AiohttpClientFixture,
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
        config = PrometheusExporterConfig(
            "test-exporter",
            "1.2.3",
            "A test exporter",
            ["0.0.0.0", "::1"],
            8000,
            ssl_context=ssl_context,
        )
        exporter = PrometheusExporter(config, registry)
        await exporter._log_startup_message(exporter.app)
        assert log.has(
            "listening", url=f"{protocol}://0.0.0.0:8000", level="info"
        )
        assert log.has(
            "listening", url=f"{protocol}://[::1]:8000", level="info"
        )
