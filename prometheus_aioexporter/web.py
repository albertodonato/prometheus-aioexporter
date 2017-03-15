'''AioHTTP application for exposing metrics to Prometheus.'''

from textwrap import dedent

from aiohttp.web import Application, Response

from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from .metric import get_registry_metrics


class PrometheusExporterApplication(Application):
    '''A web application exposing Prometheus metrics.'''

    _update_handler = None

    def __init__(self, name, description, host, port, registry, **kwargs):
        super().__init__(**kwargs)
        self.name = name
        self.description = description
        self.host = host
        self.port = port
        self.registry = registry
        self._setup_routes()
        self.on_startup.append(self._log_startup_message)

    def set_metric_update_handler(self, handler):
        '''Set a handler to update metrics.

        The provided function is called at every request with a dict as
        argument, mapping metric names to metrics.

        '''
        self._update_handler = handler

    def _log_startup_message(self, app):
        '''Log message about application startup.'''
        self.logger.info(
            'Listening on http://{}:{}'.format(self.host, self.port))

    def _setup_routes(self):
        self.router.add_get('/', self._handle_home)
        self.router.add_get('/metrics', self._handle_metrics)

    async def _handle_home(self, request):
        '''Home page request handler.'''
        if self.description:
            title = '{app.name} - {app.description}'.format(app=self)
        else:
            title = self.name

        text = dedent('''<!DOCTYPE html>
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

    async def _handle_metrics(self, request):
        '''Handler for metrics.'''
        if self._update_handler:
            self._update_handler(get_registry_metrics(self.registry))
        body = generate_latest(self.registry)
        response = Response(body=body)
        response.content_type = CONTENT_TYPE_LATEST
        return response
