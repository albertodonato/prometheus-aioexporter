"""Run a web server providing a Prometheus metrics endpoint."""

from collections.abc import Iterable
from copy import deepcopy
import os
from pathlib import Path
import ssl
import sys
import typing as t

from aiohttp.web import Application
import click
from dotenv import load_dotenv
from prometheus_client import ProcessCollector
from prometheus_client.metrics import MetricWrapperBase
import structlog

from ._log import LogFormat, LogLevel, setup_logging
from ._metric import (
    MetricConfig,
    MetricsRegistry,
)
from ._web import PrometheusExporter


class Arguments:
    """Holds parsed arguments for a script."""

    def __init__(self, **values: t.Any) -> None:
        self._values = values

    def __repr__(self) -> str:
        args = ", ".join(
            f"{name}={value!r}" for name, value in sorted(self._values.items())
        )
        return f"{self.__class__.__name__}({args})"

    def __eq__(self, other: t.Any) -> bool:
        if not isinstance(other, Arguments):
            return NotImplemented
        return self._values == other._values

    def __getattr__(self, name: str) -> t.Any:
        try:
            return self._values[name]
        except KeyError:
            raise AttributeError(
                f"'{self.__class__.__name__}' has no attribute '{name}'"
            )

    def dict(self) -> dict[str, t.Any]:
        """Return a dictionary with the arguments."""
        return deepcopy(self._values)


class PrometheusExporterScript:
    """Expose metrics to Prometheus."""

    # Name of the script, can be set by subsclasses.
    name: str = "prometheus-exporter"

    # Exporter version, can be set by subclasses. If not defined, it will be
    # detected from the package version
    version: str | None = None

    # Default port for the exporter, can be changed by subclasses.
    default_port: int = 9090

    # Default path under which metrics are exposed, can be changed by
    # subclasses.
    default_metrics_path: str = "/metrics"

    # Prefix for environment variables, can be changed by subclasses.
    # Environment variables for command line options are composed based on the
    # option name as "<PREFIX>_<UPPERCASE_NAME>".
    envvar_prefix: str = "EXP"

    # Registry for handling metrics.
    registry: MetricsRegistry
    # Structured logger for the exporter.
    logger: structlog.stdlib.BoundLogger

    def __init__(self) -> None:
        self.registry = MetricsRegistry()
        self.logger = structlog.get_logger()
        self.command = self._setup_command()

    def __call__(self, *args: str) -> None:
        self._process_dotenv()
        self.command(args=args or None)

    @property
    def description(self) -> str:
        """Service description.

        By default, return the class docstring.

        """
        return self.__doc__ or ""

    def command_line_parameters(self) -> list[click.Parameter]:
        """Add command line options and parameters.

        Subclasses can implement this, returning a list of parameters
        (e.g. click.Option or click.Argument) to add to the parser.

        """
        return []

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

    def configure(self, args: Arguments) -> None:
        """Perform additional confguration steps at script startup.

        Subclasses can implement this.

        """

    def create_metrics(
        self, metric_configs: Iterable[MetricConfig]
    ) -> dict[str, MetricWrapperBase]:
        """Create and register metrics from a list of MetricConfigs."""
        return self.registry.create_metrics(metric_configs)

    def _process_dotenv(self) -> None:
        dotenv_file = Path(os.getenv(f"{self.envvar_prefix}_DOTENV", ".env"))
        if not dotenv_file.is_file():
            return

        self.logger.debug("load dotenv", path=str(dotenv_file.absolute()))
        load_dotenv(dotenv_file)

    def _base_parameters(self) -> list[click.Parameter]:
        return [
            click.Option(
                ["-H", "--host"],
                help="host addresses to bind",
                type=str,
                default=["localhost"],
                multiple=True,
                show_default=True,
                show_envvar=True,
            ),
            click.Option(
                ["-p", "--port"],
                help="port to run the webserver on",
                type=int,
                default=self.default_port,
                show_default=True,
                show_envvar=True,
            ),
            click.Option(
                ["--metrics-path"],
                help="path under which metrics are exposed",
                type=str,
                default=self.default_metrics_path,
                show_default=True,
                show_envvar=True,
            ),
            click.Option(
                ["-L", "--log-level"],
                help="minimum level for log messages",
                type=click.Choice(LogLevel, case_sensitive=False),
                default=LogLevel.INFO,
                show_default=True,
                show_envvar=True,
            ),
            click.Option(
                ["--log-format"],
                help="log output format",
                type=click.Choice(LogFormat, case_sensitive=False),
                default=LogFormat.PLAIN,
                show_default=True,
                show_envvar=True,
            ),
            click.Option(
                ["--process-stats"],
                help="include process stats in metrics",
                type=bool,
                is_flag=True,
                show_default=True,
                show_envvar=True,
            ),
            click.Option(
                ["--ssl-private-key"],
                help="full path to the ssl private key",
                type=click.Path(exists=True, dir_okay=False, path_type=Path),
                show_envvar=True,
            ),
            click.Option(
                ["--ssl-public-key"],
                help="full path to the ssl public key",
                type=click.Path(exists=True, dir_okay=False, path_type=Path),
                show_envvar=True,
            ),
            click.Option(
                ["--ssl-ca"],
                help="full path to the ssl certificate authority (CA)",
                type=click.Path(exists=True, dir_okay=False, path_type=Path),
                show_envvar=True,
            ),
        ]

    def _setup_command(self) -> click.Command:
        params = self._base_parameters() + self.command_line_parameters()
        command = click.Command(
            name=self.name,
            help=self.description,
            context_settings={"auto_envvar_prefix": self.envvar_prefix},
            params=params,
            callback=self._command_callback,
        )
        command = click.version_option(
            version=self.version, prog_name=self.name
        )(command)
        return command

    def _command_callback(self, **kwargs: t.Any) -> None:
        try:
            self._execute(Arguments(**kwargs))
        except Exception as e:
            self.logger.exception("exception", exception=e)
            sys.exit(1)

    def _execute(self, args: Arguments) -> None:
        setup_logging(args.log_format, args.log_level)
        self.logger.info(
            "startup", version=self.version, python_version=sys.version
        )
        self.logger.debug("configuration", **args.dict())
        self._configure_registry(include_process_stats=args.process_stats)
        self.configure(args)
        exporter = self._get_exporter(args)
        exporter.run()

    def _configure_registry(self, include_process_stats: bool = False) -> None:
        if include_process_stats:
            self.registry.register_additional_collector(
                ProcessCollector(registry=None)
            )

    def _get_ssl_context(self, args: Arguments) -> ssl.SSLContext | None:
        if not all((args.ssl_private_key, args.ssl_public_key)):
            return None
        ssl_context = ssl.create_default_context(
            purpose=ssl.Purpose.CLIENT_AUTH, cafile=args.ssl_ca
        )
        ssl_context.load_cert_chain(args.ssl_public_key, args.ssl_private_key)
        return ssl_context

    def _get_exporter(self, args: Arguments) -> PrometheusExporter:
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
