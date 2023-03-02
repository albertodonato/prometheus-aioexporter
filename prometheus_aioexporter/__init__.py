"""Asyncio library for creating Prometheus exporters."""

from packaging.version import parse
from pkg_resources import get_distribution

from .metric import (
    MetricConfig,
    MetricsRegistry,
)
from .script import PrometheusExporterScript

__all__ = [
    "__version__",
    "MetricConfig",
    "MetricsRegistry",
    "PrometheusExporterScript",
]

__version__ = parse(get_distribution("prometheus-aioexporter").version)
