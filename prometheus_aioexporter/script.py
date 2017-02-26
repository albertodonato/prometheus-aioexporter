import sys
import logging
import argparse
import asyncio

from aiohttp import web

from prometheus_client import CollectorRegistry, ProcessCollector

from toolrack.script import Script, ErrorExitMessage
from toolrack.log import setup_logger

from .metric import create_metrics, InvalidMetricType
from .web import PrometheusExporterApplication


class PrometheusExporterScript(Script):
    '''Expose metrics to Prometheus.'''

    # Name of the script, can be set by subsclasses.
    name = 'prometheus-exporter'

    # Service description, can be set by subclasses.
    description = __doc__

    def __init__(self, stdout=None, stderr=None, loop=None):
        super().__init__(stdout=stdout, stderr=stderr)
        self.loop = loop or asyncio.get_event_loop()
        self.registry = CollectorRegistry(auto_describe=True)

    def configure_argument_parser(self, parser):
        '''Add configuration to the ArgumentParser.

        Subclasses can implement this to add options to the ArgumentParser for
        the script.

        '''

    def on_application_startup(self, application):
        '''Handler run at Application startup.

        Subclasses can implement this to perform operations as part of
        Application.on_startup handler.

        '''

    def on_application_shutdown(self, application):
        '''Handler run at Application shutdown.

        Subclasses can implement this to perform operations as part of
        Application.on_shutdown handler.

        '''

    def configure(self, args):
        '''Perform additional confguration steps at script startup.

        Subclasses can implement this.

        '''

    def create_metrics(self, metric_configs):
        '''Create and register metrics from a list of MetricConfigs.'''
        try:
            return create_metrics(metric_configs, self.registry)
        except InvalidMetricType as error:
            raise ErrorExitMessage(str(error))

    def get_parser(self):
        parser = argparse.ArgumentParser(
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            description=self.description)
        parser.add_argument(
            '-H', '--host', default='localhost', help='host address to bind')
        parser.add_argument(
            '-p', '--port', type=int, default=9090,
            help='port to run the webserver on')
        parser.add_argument(
            '-L', '--log-level', default='WARNING',
            choices=['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'],
            help='minimum level for log messages')
        parser.add_argument(
            '--process-stats', action='store_true',
            help='include process stats in metrics')
        self.configure_argument_parser(parser)
        return parser

    def main(self, args):
        self._setup_logging(args.log_level)
        self._configure_registry(include_process_stats=args.process_stats)
        self.configure(args)
        app = self._create_application(args)
        self._run_application(args.host, args.port, app)

    def _setup_logging(self, log_level):
        '''Setup logging for the application and aiohttp.'''
        level = getattr(logging, log_level)
        names = (
            'aiohttp.access', 'aiohttp.internal', 'aiohttp.server',
            'aiohttp.web', self.name)
        for name in names:
            setup_logger(name=name, stream=sys.stderr, level=level)

    def _configure_registry(self, include_process_stats=False):
        '''Return a metrics registry.'''
        if include_process_stats:
            ProcessCollector(registry=self.registry)

    def _create_application(self, args):
        '''Create the application to export metrics.'''
        app = PrometheusExporterApplication(
            self.name, self.description, args.host, args.port, self.registry,
            loop=self.loop)
        app.on_startup.append(self.on_application_startup)
        app.on_shutdown.append(self.on_application_shutdown)
        return app

    def _run_application(self, host, port, application):
        '''Run the application on the specified host and port.'''
        web.run_app(
            application, host=host, port=port,
            print=lambda *args, **kargs: None,
            access_log_format='%a "%r" %s %b "%{Referrer}i" "%{User-Agent}i"')
