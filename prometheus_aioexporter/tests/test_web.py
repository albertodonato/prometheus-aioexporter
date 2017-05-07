from aiohttp.test_utils import (
    AioHTTPTestCase,
    unittest_run_loop)

from prometheus_client import CollectorRegistry, Gauge, Histogram

from ..web import PrometheusExporterApplication


class PrometheusExporterApplicationTests(AioHTTPTestCase):

    def setUp(self):
        self.registry = CollectorRegistry(auto_describe=True)
        super().setUp()

    async def get_application(self):
        return PrometheusExporterApplication(
            'test-app', 'A test application', 'localhost', 8000, self.registry)

    @unittest_run_loop
    async def test_homepage(self):
        '''The homepage shows an HTML page.'''
        request = await self.client.request('GET', '/')
        self.assertEqual(request.status, 200)
        self.assertEqual(request.content_type, 'text/html')
        text = await request.text()
        self.assertIn('<title>test-app - A test application</title>', text)

    @unittest_run_loop
    async def test_homepage_no_description(self):
        '''The title is set to just the name if no descrption is present.'''
        self.app.description = None
        request = await self.client.request('GET', '/')
        self.assertEqual(request.status, 200)
        self.assertEqual(request.content_type, 'text/html')
        text = await request.text()
        self.assertIn('<title>test-app</title>', text)

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

    @unittest_run_loop
    async def test_metrics_update_handler(self):
        '''set_metric_update_handler sets a handler called with metrics.'''
        args = []

        def update_handler(metrics):
            args.append(metrics)

        self.app.set_metric_update_handler(update_handler)
        # add a test metric
        metric1 = Gauge('metric1', 'A test gauge', registry=self.registry)
        metric2 = Histogram(
            'metric2', 'A test histogram', registry=self.registry)
        await self.client.request('GET', '/metrics')
        self.assertEqual(args, [{'metric1': metric1, 'metric2': metric2}])
