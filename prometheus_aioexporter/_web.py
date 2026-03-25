"""AioHTTP application for exposing metrics to Prometheus."""

from collections.abc import (
    Awaitable,
    Callable,
)
from dataclasses import dataclass, field
import logging
from ssl import SSLContext
from textwrap import dedent
import typing as t

from aiohttp.web import (
    AppKey,
    Application,
    Request,
    Response,
    run_app,
)
from prometheus_client.metrics import MetricWrapperBase
import structlog

from ._log import AccessLogger
from ._metric import MetricsRegistry

# Signature for update handler
UpdateHandler = Callable[[dict[str, MetricWrapperBase]], Awaitable[None]]

# The application key to get the exporter from the configuration.
EXPORTER_APP_KEY: AppKey["PrometheusExporter"] = AppKey("exporter")


@dataclass(frozen=True)
class PrometheusExporterConfig:
    name: str
    version: str
    description: str
    hosts: list[str]
    port: int
    metrics_path: str = "/metrics"
    ssl_context: SSLContext | None = None
    server_version: str = field(init=False)

    def __post_init__(self):
        object.__setattr__(
            self, "server_version", f"{self.name}/{self.version}"
        )


class PrometheusExporter:
    """Export Prometheus metrics via a web application."""

    config: PrometheusExporterConfig
    registry: MetricsRegistry
    app: Application

    _update_handler: UpdateHandler | None = None

    def __init__(
        self,
        config: PrometheusExporterConfig,
        registry: MetricsRegistry,
        logger: structlog.stdlib.BoundLogger | None = None,
    ) -> None:
        self.config = config
        self.registry = registry
        self.logger = logger or structlog.get_logger()
        self.app = self._make_application()

    def set_metric_update_handler(self, handler: UpdateHandler) -> None:
        """Set a handler to update metrics.

        The provided coroutine function is called at every request with a dict
        as argument, mapping metric names to metrics.  The signature is the
        following:

          async def update_handler(metrics: dict[str, MetricWrapperBase]) -> None:

        """
        self._update_handler = handler

    def run(self) -> None:
        """Run the :class:`aiohttp.web.Application` for the exporter."""
        run_app(
            self.app,
            host=self.config.hosts,
            port=self.config.port,
            print=lambda *args, **kargs: None,
            access_log_class=AccessLogger,
            ssl_context=self.config.ssl_context,
        )

    def _make_application(self) -> Application:
        """Setup an :class:`aiohttp.web.Application`."""
        app = Application(logger=t.cast(logging.Logger, self.logger))
        app[EXPORTER_APP_KEY] = self
        app.router.add_get("/", self._handle_home)
        app.router.add_get(self.config.metrics_path, self._handle_metrics)
        app.on_startup.append(self._log_startup_message)

        async def on_prepare(request: Request, response: Response) -> None:
            response.headers["Server"] = self.config.server_version

        app.on_response_prepare.append(on_prepare)

        return app

    async def _log_startup_message(self, app: Application) -> None:
        """Log message about application startup."""
        for host in self.config.hosts:
            if ":" in host:
                host = f"[{host}]"
            protocol = "https" if self.config.ssl_context else "http"
            self.logger.info(
                "listening", url=f"{protocol}://{host}:{self.config.port}"
            )

    async def _handle_home(self, request: Request) -> Response:
        """Home page request handler."""
        text = dedent(
            f"""<!DOCTYPE html>
            <html>
              <head>
                <title>{self.config.name}</title>
                <meta name="generator" content="{self.config.name}">
              </head>
              <body>
                <h1>{self.config.name}</h1>
                <p>{self.config.description}</p>
                <p>
                  Metric are exported at the
                  <a href=".{self.config.metrics_path}">{self.config.metrics_path}</a>
                  endpoint.
                </p>
              </body>
            </html>
            """
        )
        return Response(content_type="text/html", text=text)

    async def _handle_metrics(self, request: Request) -> Response:
        """Handler for metrics."""
        if self._update_handler:
            await self._update_handler(self.registry.get_metrics())
        accept_header = request.headers.get("Accept", "")
        encoded = self.registry.encode_metrics(accept_header=accept_header)
        response = Response(body=encoded.content)
        response.content_type = encoded.content_type
        return response
