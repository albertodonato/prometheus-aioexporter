"""Helpers around prometheus_client to create and register metrics."""

from collections.abc import Iterable
from dataclasses import (
    dataclass,
    field,
)
from typing import Any

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Enum,
    Gauge,
    Histogram,
    Info,
    Summary,
    generate_latest,
)
from prometheus_client.metrics import MetricWrapperBase
from prometheus_client.registry import Collector


@dataclass(frozen=True)
class MetricType:
    """Details about a metric type."""

    cls: type[MetricWrapperBase]
    options: list[str] = field(default_factory=list)


# Map metric types to their MetricTypes
METRIC_TYPES: dict[str, MetricType] = {
    "counter": MetricType(cls=Counter),
    "enum": MetricType(cls=Enum, options=["states"]),
    "gauge": MetricType(cls=Gauge),
    "histogram": MetricType(cls=Histogram, options=["buckets"]),
    "info": MetricType(cls=Info),
    "summary": MetricType(cls=Summary),
}


@dataclass
class MetricConfig:
    """Configuration for a metric."""

    name: str
    description: str
    type: str
    labels: Iterable[str] = field(default_factory=tuple)
    config: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.labels = tuple(sorted(self.labels))
        if self.type not in METRIC_TYPES:
            raise InvalidMetricType(self.name, self.type)


class InvalidMetricType(Exception):
    """Raised when invalid metric type is found."""

    def __init__(self, name: str, invalid_type: str):
        self.name = name
        self.invalid_type = invalid_type
        type_list = ", ".join(sorted(METRIC_TYPES))
        super().__init__(
            f"Invalid type for {self.name}: must be one of {type_list}"
        )


class MetricsRegistry:
    """A registry for metrics."""

    registry: CollectorRegistry

    def __init__(self) -> None:
        self.registry = CollectorRegistry(auto_describe=True)
        self._metrics: dict[str, MetricWrapperBase] = {}

    def create_metrics(
        self, configs: Iterable[MetricConfig]
    ) -> dict[str, MetricWrapperBase]:
        """Create Prometheus metrics from a list of MetricConfigs."""
        metrics: dict[str, MetricWrapperBase] = {
            config.name: self._register_metric(config) for config in configs
        }
        self._metrics.update(metrics)
        return metrics

    def get_metric(
        self, name: str, labels: dict[str, str] | None = None
    ) -> MetricWrapperBase:
        """Return a metric, optionally configured with labels."""
        metric = self._metrics[name]
        if labels:
            return metric.labels(**labels)

        return metric

    def get_metrics(self) -> dict[str, MetricWrapperBase]:
        """Return a dict mapping names to metrics."""
        return self._metrics.copy()

    def register_additional_collector(self, collector: Collector) -> None:
        """Registrer an additional collector or metric.

        Metric(s) for the collector will not be include in the result of
        get_metrics.

        """
        self.registry.register(collector)

    def generate_metrics(self) -> bytes:
        """Generate text with metrics values from the registry."""
        return bytes(generate_latest(self.registry))

    def _register_metric(self, config: MetricConfig) -> MetricWrapperBase:
        metric_type = METRIC_TYPES[config.type]
        options = {
            key: value
            for key, value in config.config.items()
            if key in metric_type.options
        }
        return metric_type.cls(
            config.name,
            config.description,
            labelnames=config.labels,
            registry=self.registry,
            **options,
        )
