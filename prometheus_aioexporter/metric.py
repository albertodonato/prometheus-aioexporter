"""Helpers around prometheus-client to create and register metrics."""

from collections import namedtuple
from typing import (
    Dict,
    Iterable,
    NamedTuple,
    Union,
)

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Enum,
    Gauge,
    generate_latest,
    Histogram,
    Info,
    Metric,
    Summary,
)


class MetricType(NamedTuple):
    """Details about a metric type."""

    cls: Metric
    options: Dict[str, str] = {}


# Map metric types to their MetricTypes
METRIC_TYPES: Dict[str, MetricType] = {
    'counter': MetricType(cls=Counter, options={'labels': 'labelnames'}),
    'enum': MetricType(
        cls=Enum, options={
            'labels': 'labelnames',
            'states': 'states'
        }),
    'gauge': MetricType(cls=Gauge, options={'labels': 'labelnames'}),
    'histogram': MetricType(
        cls=Histogram, options={
            'labels': 'labelnames',
            'buckets': 'buckets'
        }),
    'info': MetricType(cls=Info, options={'labels': 'labelnames'}),
    'summary': MetricType(cls=Summary, options={'labels': 'labelnames'})
}


class MetricConfig(namedtuple('MetricConfig',
                              ['name', 'description', 'type', 'config'])):
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

    registry: CollectorRegistry

    def __init__(self):
        self.registry = CollectorRegistry(auto_describe=True)
        self._metrics: Dict[str, Metric] = {}

    def create_metrics(self,
                       configs: Iterable[MetricConfig]) -> Dict[str, Metric]:
        """Create Prometheus metrics from a list of MetricConfigs."""
        metrics: Dict[str, Metric] = {
            config.name: self._register_metric(config)
            for config in configs
        }
        self._metrics.update(metrics)
        return metrics

    def get_metric(
            self, name: str,
            labels: Union[Dict[str, str], None] = None) -> Metric:
        """Return a metric, optionally configured with labels."""
        metric = self._metrics[name]
        if labels:
            return metric.labels(**labels)

        return metric

    def get_metrics(self) -> Dict[str, Metric]:
        """Return a dict mapping names to metrics."""
        return self._metrics.copy()

    def register_additional_collector(self, collector):
        """Registrer an additional collector or metric.

        Metric(s) for the collector will not be include in the result of
        get_metrics.

        """
        self.registry.register(collector)

    def generate_metrics(self) -> bytes:
        """Generate text with metrics values from the registry."""
        return bytes(generate_latest(self.registry))

    def _register_metric(self, config: MetricConfig) -> Metric:
        metric_type = METRIC_TYPES[config.type]
        options = {
            metric_type.options[key]: value
            for key, value in config.config.items()
            if key in metric_type.options
        }
        return metric_type.cls(
            config.name, config.description, registry=self.registry, **options)
