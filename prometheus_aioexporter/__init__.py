"""Asyncio library for creating Prometheus exporters."""

from distutils.version import LooseVersion

import pkg_resources

from .metric import (
    MetricConfig,
    MetricsRegistry,
)
from .script import PrometheusExporterScript

__all__ = [
    '__version__', 'MetricConfig', 'MetricsRegistry',
    'PrometheusExporterScript'
]

__version__ = LooseVersion(
    pkg_resources.require('prometheus_aioexporter')[0].version)
