"""Run a web server providing a Prometheus metrics endpoint."""

import argparse
import logging
import ssl
import sys
from collections.abc import Iterable
from ssl import SSLContext
from typing import (
    IO,
)

from aiohttp.web import Application
from prometheus_client import (
    Metric,
    ProcessCollector,
)
from toolrack.log import setup_logger
from toolrack.script import Script

from .metric import (
    MetricConfig,
    MetricsRegistry,
)
from .web import PrometheusExporter


class PrometheusExporterScript(Script):  # type: ignore
    """Expose metrics to Prometheus."""

    #: Name of the script, can be set by subsclasses.
    name = "prometheus-exporter"

    # The defualt port for the exporter, can be changed by subclasses.
    default_port = 9090

    # The default path under which metrics are exposed.
    default_metrics_path = "/metrics"

    registry: MetricsRegistry

    def __init__(
            self, stdout: IO[bytes] | None = None,
            stderr: IO[bytes] | None = None
    ) -> None:
        super().__init__(stdout=stdout, stderr=stderr)
        self.registry = MetricsRegistry()

    @property
    def description(self) -> str:
        """Service description.

        By default, return the class docstring.

        """
        return self.__doc__ or ""

    @property
    def logger(self) -> logging.Logger:
        """A logger for the script."""
        return logging.getLogger(name=self.name)

    def configure_argument_parser(
            self, parser: argparse.ArgumentParser
    ) -> None:
        """Add configuration to the ArgumentParser.

        Subclasses can implement this to add options to the ArgumentParser for
        the script.

        """

    async def on_application_startup(self, application: Application) -> None:
        """Handler run at Application startup.

        This must be a coroutine.

        Subclasses can implement this to perform operations as part of
        Application.on_startup handler.

        """

    async def on_application_shutdown(self, application: Application) -> None:
        """Handler run at Application shutdown.

        This must be a coroutine.

        Subclasses can implement this to perform operations as part of
        Application.on_shutdown handler.

        """

    def configure(self, args: argparse.Namespace) -> None:
        """Perform additional confguration steps at script startup.

        Subclasses can implement this.

        """

    def create_metrics(
            self, metric_configs: Iterable[MetricConfig]
    ) -> dict[str, Metric]:
        """Create and register metrics from a list of MetricConfigs."""
        return self.registry.create_metrics(metric_configs)

    def get_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            description=self.description,
        )
        parser.add_argument(
            "-H",
            "--host",
            default=["localhost"],
            nargs="+",
            help="host addresses to bind",
        )
        parser.add_argument(
            "-p",
            "--port",
            type=int,
            default=self.default_port,
            help="port to run the webserver on",
        )
        parser.add_argument(
            "--metrics-path",
            default=self.default_metrics_path,
            help="path under which metrics are exposed",
        )
        parser.add_argument(
            "-L",
            "--log-level",
            default="WARNING",
            choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
            help="minimum level for log messages",
        )
        parser.add_argument(
            "--process-stats",
            action="store_true",
            help="include process stats in metrics",
        )
        parser.add_argument(
            "--ssl-private-key",
            type=argparse.FileType('r'),
            help="full path to the ssl private key",
        )
        parser.add_argument(
            "--ssl-public-key",
            type=argparse.FileType('r'),
            help="full path to the ssl public key",
        )
        parser.add_argument(
            "--ssl-ca",
            type=argparse.FileType('r'),
            help="full path to the ssl certificate authority (CA)",
        )
        self.configure_argument_parser(parser)
        return parser

    def main(self, args: argparse.Namespace) -> None:
        self._setup_logging(args.log_level)
        self._configure_registry(include_process_stats=args.process_stats)
        self.configure(args)
        exporter = self._get_exporter(args)
        exporter.run()

    def _setup_logging(self, log_level: str) -> None:
        """Setup logging for the application and aiohttp."""
        level = getattr(logging, log_level)
        names = (
            "aiohttp.access",
            "aiohttp.internal",
            "aiohttp.server",
            "aiohttp.web",
            self.name,
        )
        for name in names:
            setup_logger(name=name, stream=sys.stderr, level=level)

    def _configure_registry(self, include_process_stats: bool = False) -> None:
        """Configure the MetricRegistry."""
        if include_process_stats:
            self.registry.register_additional_collector(
                ProcessCollector(registry=None)
            )

    def _get_ssl_context(self, args: argparse.Namespace) -> SSLContext | None:
        if args.ssl_private_key is None or args.ssl_public_key is None:
            return None
        cafile = None
        if args.ssl_ca:
            cafile = args.ssl_ca
        ssl_context = ssl.create_default_context(
            purpose=ssl.Purpose.CLIENT_AUTH, cafile=cafile
        )
        ssl_context.load_cert_chain(args.ssl_public_key, args.ssl_private_key)

        return ssl_context

    def _get_exporter(self, args: argparse.Namespace) -> PrometheusExporter:
        """Return a :class:`PrometheusExporter` configured with args."""
        exporter = PrometheusExporter(
            self.name,
            self.description,
            args.host,
            args.port,
            self.registry,
            metrics_path=args.metrics_path,
            ssl_context=self._get_ssl_context(args),
        )
        exporter.app.on_startup.append(self.on_application_startup)
        exporter.app.on_shutdown.append(self.on_application_shutdown)
        return exporter
