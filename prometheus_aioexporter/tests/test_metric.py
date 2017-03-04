from unittest import TestCase

from prometheus_client import CollectorRegistry, Gauge, Histogram

from ..metric import (
    MetricConfig,
    InvalidMetricType,
    create_metrics,
    get_registry_metrics
)


class MetricConfigTests(TestCase):

    def test_invalid_metric_type(self):
        '''An invalid metric type raises an error.'''
        with self.assertRaises(InvalidMetricType) as cm:
            MetricConfig('m1', 'desc1', 'unknown', {})
        self.assertEqual(
            str(cm.exception),
            'Invalid type for m1: must be one of counter, gauge,'
            ' histogram, summary')


class CreateMetricsTests(TestCase):

    def setUp(self):
        super().setUp()
        self.registry = CollectorRegistry()

    def test_metrics_from_config(self):
        '''Prometheus metrics are created from the specified config.'''
        configs = [
            MetricConfig('m1', 'desc1', 'counter', {}),
            MetricConfig('m2', 'desc2', 'histogram', {})]
        metrics = create_metrics(configs, self.registry)
        self.assertEqual(len(metrics), 2)
        self.assertEqual(metrics['m1']._type, 'counter')
        self.assertEqual(metrics['m2']._type, 'histogram')

    def test_metrics_config(self):
        '''Metric configs are applied.'''
        configs = [
            MetricConfig('m1', 'desc1', 'histogram', {'buckets': [10, 20]})]
        metrics = create_metrics(configs, self.registry)
        # The two specified bucket plus +Inf
        self.assertEqual(len(metrics['m1']._buckets), 3)

    def test_metrics_config_ignores_unknown(self):
        '''Unknown metric configs are ignored and don't cause an error.'''
        configs = [
            MetricConfig('m1', 'desc1', 'gauge', {'unknown': 'value'})]
        metrics = create_metrics(configs, self.registry)
        self.assertEqual(len(metrics), 1)


class GetRegistryMetricsTests(TestCase):

    def test_get_registry_metrics(self):
        '''get_registry_metrics returns a dict with metrics.'''
        registry = CollectorRegistry()
        metric1 = Gauge('metric1', 'A test gauge', registry=registry)
        metric2 = Histogram('metric2', 'A test histogram', registry=registry)
        metrics = get_registry_metrics(registry)
        self.assertEqual(metrics, {'metric1': metric1, 'metric2': metric2})
