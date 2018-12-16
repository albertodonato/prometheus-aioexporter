"""AioHTTP application for exposing metrics to Prometheus."""

from textwrap import dedent
from typing import (
    Awaitable,
    Callable,
    Iterable,
    Union,
)

from aiohttp.web import (
    Application,
    Request,
    Response,
    run_app,
)
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Metric,
)

from .metric import MetricsRegistry

# Signature for update handler
UpdateHandler = Callable[[Iterable[Metric]], Awaitable[None]]


class PrometheusExporter:
    """Export Prometheus metrics via a web application."""

    name: str
    descrption: str
    host: str
    port: int
    register: MetricsRegistry
    app: Application

    _update_handler: Union[UpdateHandler, None] = None

    def __init__(
            self, name: str, description: str, host: str, port: int,
            registry: MetricsRegistry):
        self.name = name
        self.description = description
        self.host = host
        self.port = port
        self.registry = registry
        self.app = self._make_application()

    def set_metric_update_handler(self, handler: UpdateHandler):
        """Set a handler to update metrics.

        The provided coroutine function is called at every request with a dict
        as argument, mapping metric names to metrics.  The signature is the
        following:

          async def update_handler(metrics):

        """
        self._update_handler = handler

    def run(self):
        """Run the :class:`aiohttp.web.Application` for the exporter."""
        run_app(
            self.app,
            host=self.host,
            port=self.port,
            print=lambda *args, **kargs: None,
            access_log_format='%a "%r" %s %b "%{Referrer}i" "%{User-Agent}i"')

    def _make_application(self) -> Application:
        """Setup an :class:`aiohttp.web.Application`."""
        app = Application()
        app['exporter'] = self
        app.router.add_get('/', self._handle_home)
        app.router.add_get('/metrics', self._handle_metrics)
        app.on_startup.append(self._log_startup_message)
        return app

    async def _log_startup_message(self, app: Application):
        """Log message about application startup."""
        self.app.logger.info(
            'Listening on http://{}:{}'.format(self.host, self.port))

    async def _handle_home(self, request: Request) -> Response:
        """Home page request handler."""
        if self.description:
            title = '{app.name} - {app.description}'.format(app=self)
        else:
            title = self.name

        text = dedent(
            '''<!DOCTYPE html>
          <html>
            <head>
              <title>{title}</title>
            </head>
            <body>
              <h1>{title}</h1>
              <p>
                Metric are exported at the
                <a href="/metrics">/metrics</a> endpoint.
              </p>
            </body>
          </html>
        ''').format(title=title)
        return Response(content_type='text/html', text=text)

    async def _handle_metrics(self, request: Request) -> Response:
        """Handler for metrics."""
        if self._update_handler:
            await self._update_handler(self.registry.get_metrics())
        response = Response(body=self.registry.generate_metrics())
        response.content_type = CONTENT_TYPE_LATEST
        return response
