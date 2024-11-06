"""Run a web server providing a Prometheus metrics endpoint."""

import argparse
from collections.abc import Iterable
import ssl
from typing import IO, cast

from aiohttp.web import Application
from prometheus_client import ProcessCollector
from prometheus_client.metrics import MetricWrapperBase
import structlog
from toolrack.script import Script

from ._log import LogFormat, LogLevel, setup_logging
from ._metric import (
    MetricConfig,
    MetricsRegistry,
)
from ._web import PrometheusExporter


class PrometheusExporterScript(Script):
    """Expose metrics to Prometheus."""

    #: Name of the script, can be set by subsclasses.
    name = "prometheus-exporter"

    #: Default port for the exporter, can be changed by subclasses.
    default_port = 9090

    #: Default path under which metrics are exposed.
    default_metrics_path = "/metrics"

    #: Registry for handling metrics.
    registry: MetricsRegistry
    #: Structured logger for the exporter.
    logger: structlog.BoundLogger

    def __init__(
        self,
        stdout: IO[bytes] | None = None,
        stderr: IO[bytes] | None = None,
        logger: structlog.BoundLogger | None = None,
    ) -> None:
        super().__init__(stdout=stdout, stderr=stderr)
        self.registry = MetricsRegistry()
        if not logger:
            logger = cast(structlog.BoundLogger, structlog.get_logger())
        self.logger = logger

    @property
    def description(self) -> str:
        """Service description.

        By default, return the class docstring.

        """
        return self.__doc__ or ""

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
    ) -> dict[str, MetricWrapperBase]:
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
            type=LogLevel,
            default=LogLevel.INFO,
            choices=[str(choice) for choice in LogLevel],
            help="minimum level for log messages",
        )
        parser.add_argument(
            "--log-format",
            default=LogFormat.PLAIN,
            choices=[str(choice) for choice in LogFormat],
            help="log output format",
        )
        parser.add_argument(
            "--process-stats",
            action="store_true",
            help="include process stats in metrics",
        )
        parser.add_argument(
            "--ssl-private-key",
            type=argparse.FileType("r"),
            help="full path to the ssl private key",
        )
        parser.add_argument(
            "--ssl-public-key",
            type=argparse.FileType("r"),
            help="full path to the ssl public key",
        )
        parser.add_argument(
            "--ssl-ca",
            type=argparse.FileType("r"),
            help="full path to the ssl certificate authority (CA)",
        )
        self.configure_argument_parser(parser)
        return parser

    def main(self, args: argparse.Namespace) -> None:
        setup_logging(args.log_format, args.log_level)
        self.logger.info("startup")
        self._configure_registry(include_process_stats=args.process_stats)
        self.configure(args)
        exporter = self._get_exporter(args)
        exporter.run()

    def _configure_registry(self, include_process_stats: bool = False) -> None:
        """Configure the MetricRegistry."""
        if include_process_stats:
            self.registry.register_additional_collector(
                ProcessCollector(registry=None)
            )

    def _get_ssl_context(
        self, args: argparse.Namespace
    ) -> ssl.SSLContext | None:
        if args.ssl_private_key is None or args.ssl_public_key is None:
            return None
        cafile = None
        if args.ssl_ca:
            cafile = args.ssl_ca.name
            args.ssl_ca.close()
        ssl_context = ssl.create_default_context(
            purpose=ssl.Purpose.CLIENT_AUTH, cafile=cafile
        )
        ssl_context.load_cert_chain(
            args.ssl_public_key.name, args.ssl_private_key.name
        )
        args.ssl_public_key.close()
        args.ssl_private_key.close()
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
            logger=self.logger,
        )
        exporter.app.on_startup.append(self.on_application_startup)
        exporter.app.on_shutdown.append(self.on_application_shutdown)
        return exporter
