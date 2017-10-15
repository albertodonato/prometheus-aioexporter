from unittest import TestCase

from ..metric import (
    MetricConfig,
    InvalidMetricType,
    MetricsRegistry)


class MetricConfigTests(TestCase):

    def test_invalid_metric_type(self):
        """An invalid metric type raises an error."""
        with self.assertRaises(InvalidMetricType) as cm:
            MetricConfig('m1', 'desc1', 'unknown', {})
        self.assertEqual(
            str(cm.exception),
            'Invalid type for m1: must be one of counter, gauge,'
            ' histogram, summary')


class MetricsRegistryTests(TestCase):

    def setUp(self):
        super().setUp()
        self.registry = MetricsRegistry()

    def test_create_metrics(self):
        """Prometheus metrics are created from the specified config."""
        configs = [
            MetricConfig('m1', 'desc1', 'counter', {}),
            MetricConfig('m2', 'desc2', 'histogram', {})]
        metrics = self.registry.create_metrics(configs)
        self.assertEqual(len(metrics), 2)
        self.assertEqual(metrics['m1']._type, 'counter')
        self.assertEqual(metrics['m2']._type, 'histogram')

    def test_create_metrics_with_config(self):
        """Metric configs are applied."""
        configs = [
            MetricConfig('m1', 'desc1', 'histogram', {'buckets': [10, 20]})]
        metrics = self.registry.create_metrics(configs)
        # The two specified bucket plus +Inf
        self.assertEqual(len(metrics['m1']._buckets), 3)

    def test_create_metrics_config_ignores_unknown(self):
        """Unknown metric configs are ignored and don't cause an error."""
        configs = [
            MetricConfig('m1', 'desc1', 'gauge', {'unknown': 'value'})]
        metrics = self.registry.create_metrics(configs)
        self.assertEqual(len(metrics), 1)

    def test_get_metrics(self):
        """get_metrics returns a dict with metrics."""
        metrics = self.registry.create_metrics(
            [MetricConfig('metric1', 'A test gauge', 'gauge', {}),
             MetricConfig('metric2', 'A test histogram', 'histogram', {})])
        self.assertEqual(self.registry.get_metrics(), metrics)

    def test_generate_metrics(self):
        """generate_metrics returns text with metrics values."""
        metrics = self.registry.create_metrics(
            [MetricConfig('test_gauge', 'A test gauge', 'gauge', {})])
        metrics['test_gauge'].set(12.3)
        text = self.registry.generate_metrics().decode('utf-8')
        self.assertIn('HELP test_gauge A test gauge', text)
        self.assertIn('test_gauge 12.3', text)
