from unittest import mock

import pytest

from ..metric import (
    MetricConfig,
    MetricsRegistry,
)
from ..web import PrometheusExporter


@pytest.fixture
def registry():
    yield MetricsRegistry()


@pytest.fixture
def exporter(registry):
    yield PrometheusExporter(
        'test-app', 'A test application', 'localhost', 8000, registry)


class TestPrometheusExporter:

    def test_app_exporter_reference(self, exporter):
        """The application has a reference to the exporter."""
        assert exporter.app['exporter'] is exporter

    def test_run(self, mocker, exporter):
        """The script starts the web application."""
        mock_run_app = mocker.patch('prometheus_aioexporter.web.run_app')
        exporter.run()
        mock_run_app.assert_called_with(
            mock.ANY,
            host='localhost',
            port=8000,
            print=mock.ANY,
            access_log_format='%a "%r" %s %b "%{Referrer}i" "%{User-Agent}i"')

    async def test_homepage(self, test_client, exporter):
        """The homepage shows an HTML page."""
        client = await test_client(exporter.app)
        request = await client.request('GET', '/')
        assert request.status == 200
        assert request.content_type == 'text/html'
        text = await request.text()
        assert '<title>test-app - A test application</title>' in text

    async def test_homepage_no_description(self, test_client, exporter):
        """The title is set to just the name if no descrption is present."""
        exporter.description = None
        client = await test_client(exporter.app)
        request = await client.request('GET', '/')
        assert request.status == 200
        assert request.content_type == 'text/html'
        text = await request.text()
        assert '<title>test-app</title>' in text

    async def test_metrics(self, test_client, exporter, registry):
        """The /metrics page display Prometheus metrics."""
        metrics = registry.create_metrics(
            [MetricConfig('test_gauge', 'A test gauge', 'gauge', {})])
        metrics['test_gauge'].set(12.3)
        client = await test_client(exporter.app)
        request = await client.request('GET', '/metrics')
        assert request.status == 200
        assert request.content_type == 'text/plain'
        text = await request.text()
        assert 'HELP test_gauge A test gauge' in text
        assert 'test_gauge 12.3' in text

    async def test_metrics_update_handler(
            self, test_client, exporter, registry):
        """set_metric_update_handler sets a handler called with metrics."""
        args = []

        async def update_handler(metrics):
            args.append(metrics)

        exporter.set_metric_update_handler(update_handler)
        metrics = registry.create_metrics(
            [
                MetricConfig('metric1', 'A test gauge', 'gauge', {}),
                MetricConfig('metric2', 'A test histogram', 'histogram', {})
            ])
        client = await test_client(exporter.app)
        await client.request('GET', '/metrics')
        assert args == [metrics]
