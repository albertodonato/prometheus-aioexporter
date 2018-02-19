from unittest import mock

from aiohttp.test_utils import (
    AioHTTPTestCase,
    unittest_run_loop)

from ..metric import (
    MetricsRegistry,
    MetricConfig)
from ..web import PrometheusExporter


class PrometheusExporterTests(AioHTTPTestCase):

    def setUp(self):
        self.registry = MetricsRegistry()
        self.exporter = PrometheusExporter(
            'test-app', 'A test application', 'localhost', 8000, self.registry)
        super().setUp()

    async def get_application(self):
        return self.exporter.app

    def test_app_exporter_reference(self):
        """The application has a reference to the exporter."""
        self.assertIs(self.app['exporter'], self.exporter)

    @mock.patch('prometheus_aioexporter.web.run_app')
    def test_run(self, mock_run_app):
        """The script starts the web application."""
        self.exporter.run()
        mock_run_app.assert_called_with(
            mock.ANY, host='localhost', port=8000, print=mock.ANY,
            access_log_format='%a "%r" %s %b "%{Referrer}i" "%{User-Agent}i"')

    @unittest_run_loop
    async def test_homepage(self):
        """The homepage shows an HTML page."""
        request = await self.client.request('GET', '/')
        self.assertEqual(request.status, 200)
        self.assertEqual(request.content_type, 'text/html')
        text = await request.text()
        self.assertIn('<title>test-app - A test application</title>', text)

    @unittest_run_loop
    async def test_homepage_no_description(self):
        """The title is set to just the name if no descrption is present."""
        self.exporter.description = None
        request = await self.client.request('GET', '/')
        self.assertEqual(request.status, 200)
        self.assertEqual(request.content_type, 'text/html')
        text = await request.text()
        self.assertIn('<title>test-app</title>', text)

    @unittest_run_loop
    async def test_metrics(self):
        """The /metrics page display Prometheus metrics."""
        metrics = self.registry.create_metrics(
            [MetricConfig('test_gauge', 'A test gauge', 'gauge', {})])
        metrics['test_gauge'].set(12.3)
        request = await self.client.request('GET', '/metrics')
        self.assertEqual(request.status, 200)
        self.assertEqual(request.content_type, 'text/plain')
        text = await request.text()
        self.assertIn('HELP test_gauge A test gauge', text)
        self.assertIn('test_gauge 12.3', text)

    @unittest_run_loop
    async def test_metrics_update_handler(self):
        """set_metric_update_handler sets a handler called with metrics."""
        args = []

        async def update_handler(metrics):
            args.append(metrics)

        self.exporter.set_metric_update_handler(update_handler)
        metrics = self.registry.create_metrics(
            [MetricConfig('metric1', 'A test gauge', 'gauge', {}),
             MetricConfig('metric2', 'A test histogram', 'histogram', {})])
        await self.client.request('GET', '/metrics')
        self.assertEqual(args, [metrics])
