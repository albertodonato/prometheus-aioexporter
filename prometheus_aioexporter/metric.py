"""Helpers around prometheus-client to create and register metrics."""

from collections import namedtuple

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    Summary,
    generate_latest)


# Map metric types to classes and allowed options
METRIC_TYPES = {
    'counter': {
        'class': Counter,
        'options': {
            'labels': 'labelnames'}},
    'gauge': {
        'class': Gauge,
        'options': {
            'labels': 'labelnames'}},
    'histogram': {
        'class': Histogram,
        'options': {
            'labels': 'labelnames',
            'buckets': 'buckets'}},
    'summary': {
        'class': Summary,
        'options': {
            'labels': 'labelnames'}}}


class MetricConfig(namedtuple(
        'MetricConfig', ['name', 'description', 'type', 'config'])):
    """Configuration for a metric."""

    def __new__(cls, name, description, typ, config):
        if typ not in METRIC_TYPES:
            raise InvalidMetricType(name, typ)
        return super().__new__(cls, name, description, typ, config)


class InvalidMetricType(Exception):
    """Raised when invalid metric type is found."""

    def __init__(self, name, invalid_type):
        self.name = name
        self.invalid_type = invalid_type
        super().__init__(
            'Invalid type for {}: must be one of {}'.format(
                self.name, ', '.join(sorted(METRIC_TYPES))))


class MetricsRegistry:
    """A registry for metrics."""

    def __init__(self):
        self.registry = CollectorRegistry(auto_describe=True)
        self._metrics = {}

    def create_metrics(self, configs):
        """Create Prometheus metrics from a list of MetricConfigs."""
        metrics = {
            config.name: self._register_metric(config)
            for config in configs}
        self._metrics.update(metrics)
        return metrics

    def get_metrics(self):
        """Return a dict mapping names to metrics."""
        return self._metrics.copy()

    def register_additional_collector(self, collector):
        """Registrer an additional collector or metric.

        Metric(s) for the collector will not be include in the result of
        get_metrics.

        """
        self.registry.register(collector)

    def generate_metrics(self):
        """Generate text with metrics values from the registry."""
        return generate_latest(self.registry)

    def _register_metric(self, config):
        metric_info = METRIC_TYPES[config.type]
        options = {
            metric_info['options'][key]: value
            for key, value in config.config.items()
            if key in metric_info['options']}
        return metric_info['class'](
            config.name, config.description, registry=self.registry, **options)
