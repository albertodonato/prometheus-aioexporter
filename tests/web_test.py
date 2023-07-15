from ssl import SSLContext
from unittest import mock

import pytest

from prometheus_aioexporter.metric import (
    MetricConfig,
    MetricsRegistry,
)
from prometheus_aioexporter.web import PrometheusExporter
from tests.conftest import ssl_context


@pytest.fixture
def registry():
    yield MetricsRegistry()


@pytest.fixture
def exporter(registry, request):
    yield PrometheusExporter(
        name="test-app",
        description="A test application",
        hosts=["localhost"],
        port=8000,
        registry=registry,
        ssl_context=request.param,
    )


@pytest.fixture
def exporter_ssl(registry, ssl_context):
    yield PrometheusExporter(
        name="test-app",
        description="A test application",
        hosts=["localhost"],
        port=8000,
        registry=registry,
        ssl_context=ssl_context,
    )


@pytest.fixture
def create_server_client(ssl_context, aiohttp_server):
    def create(exporter):
        kwargs = {}
        if exporter.ssl_context is None:
            kwargs["ssl"] = exporter.ssl_context
        return aiohttp_server(exporter.app, **kwargs)

    return create


class TestPrometheusExporter:
    @pytest.mark.parametrize("exporter", [ssl_context, None], indirect=True)
    def test_app_exporter_reference(self, exporter):
        """The application has a reference to the exporter."""
        assert exporter.app["exporter"] is exporter

    @pytest.mark.parametrize("exporter", [ssl_context, None], indirect=True)
    def test_run(self, mocker, exporter):
        """The script starts the web application."""
        mock_run_app = mocker.patch("prometheus_aioexporter.web.run_app")
        exporter.run()
        mock_run_app.assert_called_with(
            mock.ANY,
            host=["localhost"],
            port=8000,
            print=mock.ANY,
            access_log_format='%a "%r" %s %b "%{Referrer}i" "%{User-Agent}i"',
            ssl_context=exporter.ssl_context,
        )

    @pytest.mark.parametrize("exporter", [ssl_context, None], indirect=True)
    async def test_homepage(
            self,
            ssl_context_server,
            create_server_client,
            exporter,
            aiohttp_client,
    ):
        """The homepage shows an HTML page."""
        server = await create_server_client(exporter)
        client = await aiohttp_client(server)
        ssl_client_context = None
        if exporter.ssl_context is not None:
            ssl_client_context = ssl_context_server
        request = await client.request("GET", "/", ssl=ssl_client_context)
        assert request.status == 200
        assert request.content_type == "text/html"
        text = await request.text()
        assert "<title>test-app - A test application</title>" in text

    @pytest.mark.parametrize("exporter", [ssl_context, None], indirect=True)
    async def test_homepage_no_description(self, aiohttp_client, exporter):
        """The title is set to just the name if no description is present."""
        exporter.description = None
        client = await aiohttp_client(exporter.app)
        request = await client.request("GET", "/")
        assert request.status == 200
        assert request.content_type == "text/html"
        text = await request.text()
        assert "<title>test-app</title>" in text

    @pytest.mark.parametrize("exporter", [ssl_context, None], indirect=True)
    async def test_metrics(self, aiohttp_client, exporter, registry):
        """The /metrics page display Prometheus metrics."""
        metrics = registry.create_metrics(
            [MetricConfig("test_gauge", "A test gauge", "gauge", {})]
        )
        metrics["test_gauge"].set(12.3)
        client = await aiohttp_client(exporter.app)
        request = await client.request("GET", "/metrics")
        assert request.status == 200
        assert request.content_type == "text/plain"
        text = await request.text()
        assert "HELP test_gauge A test gauge" in text
        assert "test_gauge 12.3" in text

    @pytest.mark.parametrize("ssl_context", [SSLContext(), None])
    async def test_metrics_different_path(
            self, aiohttp_client, registry, ssl_context
    ):
        """The metrics path can be changed."""
        exporter = PrometheusExporter(
            "test-app",
            "A test application",
            "localhost",
            8000,
            registry,
            metrics_path="/other-path",
            ssl_context=ssl_context,
        )
        metrics = registry.create_metrics(
            [MetricConfig("test_gauge", "A test gauge", "gauge", {})]
        )
        metrics["test_gauge"].set(12.3)
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

    @pytest.mark.parametrize("exporter", [ssl_context, None], indirect=True)
    async def test_metrics_update_handler(
            self, aiohttp_client, exporter, registry
    ):
        """set_metric_update_handler sets a handler called with metrics."""
        args = []

        async def update_handler(metrics):
            args.append(metrics)

        exporter.set_metric_update_handler(update_handler)
        metrics = registry.create_metrics(
            [
                MetricConfig("metric1", "A test gauge", "gauge", {}),
                MetricConfig("metric2", "A test histogram", "histogram", {}),
            ]
        )
        client = await aiohttp_client(exporter.app)
        await client.request("GET", "/metrics")
        assert args == [metrics]

    @pytest.mark.parametrize(
        ["ssl_context", "protocol"], [(ssl_context, "https"), (None, "http")]
    )
    async def test_startup_logger(
            self, mocker, registry, ssl_context, protocol
    ):
        exporter = PrometheusExporter(
            "test-app",
            "A test application",
            ["0.0.0.0", "::1"],
            8000,
            registry,
            ssl_context=ssl_context,
        )
        mock_log = mocker.patch.object(exporter.app.logger, "info")
        await exporter._log_startup_message(exporter.app)
        assert mock_log.mock_calls == [
            mock.call(f"Listening on {protocol}://0.0.0.0:8000"),
            mock.call(f"Listening on {protocol}://[::1]:8000"),
        ]
