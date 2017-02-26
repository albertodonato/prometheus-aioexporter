from aiohttp.test_utils import (
    AioHTTPTestCase,
    unittest_run_loop)

from prometheus_client import CollectorRegistry, Gauge

from ..web import PrometheusExporterApplication


class PrometheusExporterApplicationTests(AioHTTPTestCase):

    def setUp(self):
        self.registry = CollectorRegistry(auto_describe=True)
        super().setUp()

    def get_app(self, loop):
        return PrometheusExporterApplication(
            'test-app', 'A test application', 'localhost', 8000, self.registry,
            loop=loop)

    @unittest_run_loop
    async def test_homepage(self):
        '''The homepage shows an HTML page.'''
        request = await self.client.request('GET', '/')
        self.assertEqual(request.status, 200)
        self.assertEqual(request.content_type, 'text/html')
        text = await request.text()
        self.assertIn('test-app - A test application', text)

    @unittest_run_loop
    async def test_metrics(self):
        '''The /metrics page display Prometheus metrics.'''
        # add a test metric
        metric = Gauge(
            'test_gauge', 'A test gauge', registry=self.registry)
        metric.set(12.3)
        request = await self.client.request('GET', '/metrics')
        self.assertEqual(request.status, 200)
        self.assertEqual(request.content_type, 'text/plain')
        text = await request.text()
        self.assertIn('HELP test_gauge A test gauge', text)
        self.assertIn('test_gauge 12.3', text)
