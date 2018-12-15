import pytest

from ..metric import (
    InvalidMetricType,
    MetricConfig,
    MetricsRegistry,
)


class TestMetricConfig:

    def test_invalid_metric_type(self):
        """An invalid metric type raises an error."""
        with pytest.raises(InvalidMetricType) as error:
            MetricConfig('m1', 'desc1', 'unknown', {})
        assert str(error.value) == (
            'Invalid type for m1: must be one of counter, gauge,'
            ' histogram, summary')


class TestMetricsRegistry:

    def test_create_metrics(self):
        """Prometheus metrics are created from the specified config."""
        configs = [
            MetricConfig('m1', 'desc1', 'counter', {}),
            MetricConfig('m2', 'desc2', 'histogram', {})
        ]
        metrics = MetricsRegistry().create_metrics(configs)
        assert len(metrics) == 2
        assert metrics['m1']._type == 'counter'
        assert metrics['m2']._type == 'histogram'

    def test_create_metrics_with_config(self):
        """Metric configs are applied."""
        configs = [
            MetricConfig('m1', 'desc1', 'histogram', {'buckets': [10, 20]})
        ]
        metrics = MetricsRegistry().create_metrics(configs)
        # The two specified bucket plus +Inf
        assert len(metrics['m1']._buckets) == 3

    def test_create_metrics_config_ignores_unknown(self):
        """Unknown metric configs are ignored and don't cause an error."""
        configs = [MetricConfig('m1', 'desc1', 'gauge', {'unknown': 'value'})]
        metrics = MetricsRegistry().create_metrics(configs)
        assert len(metrics) == 1

    def test_get_metrics(self):
        """get_metrics returns a dict with metrics."""
        registry = MetricsRegistry()
        metrics = registry.create_metrics(
            [
                MetricConfig('metric1', 'A test gauge', 'gauge', {}),
                MetricConfig('metric2', 'A test histogram', 'histogram', {})
            ])
        assert registry.get_metrics() == metrics

    def test_get_metric(self):
        """get_metric returns a metric."""
        configs = [
            MetricConfig(
                'm', 'A test gauge', 'gauge', {'labels': ['l1', 'l2']})
        ]
        registry = MetricsRegistry()
        registry.create_metrics(configs)
        metric = registry.get_metric('m')
        assert metric._name == 'm'
        assert metric._labelvalues == ()

    def test_get_metric_with_labels(self):
        """get_metric returns a metric configured with labels."""
        configs = [
            MetricConfig(
                'm', 'A test gauge', 'gauge', {'labels': ['l1', 'l2']})
        ]
        registry = MetricsRegistry()
        registry.create_metrics(configs)
        metric = registry.get_metric('m', {'l1': 'v1', 'l2': 'v2'})
        assert metric._labelvalues == ('v1', 'v2')

    def test_generate_metrics(self):
        """generate_metrics returns text with metrics values."""
        registry = MetricsRegistry()
        metrics = registry.create_metrics(
            [MetricConfig('test_gauge', 'A test gauge', 'gauge', {})])
        metrics['test_gauge'].set(12.3)
        text = registry.generate_metrics().decode('utf-8')
        assert 'HELP test_gauge A test gauge' in text
        assert 'test_gauge 12.3' in text
