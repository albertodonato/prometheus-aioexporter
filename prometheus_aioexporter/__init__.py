"""Asyncio library for creating Prometheus exporters."""

from distutils.version import LooseVersion

import pkg_resources

from .script import PrometheusExporterScript

__all__ = ['__version__', 'PrometheusExporterScript']

__version__ = LooseVersion(
    pkg_resources.require('prometheus_aioexporter')[0].version)
