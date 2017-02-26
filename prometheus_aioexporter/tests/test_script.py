from unittest import mock
from io import StringIO
import logging

from toolrack.script import ErrorExitMessage
from toolrack.testing.async import LoopTestCase

from ..script import PrometheusExporterScript
from ..metric import MetricConfig


class PrometheusExporterScriptTests(LoopTestCase):

    def setUp(self):
        super().setUp()
        self.script = PrometheusExporterScript(loop=self.loop)
        self.script.name = 'sample-script'
        self.script.description = 'A sample script'

    def test_configure_argument_parser(self):
        '''configure_argument_parser adds specified arguments.'''

        def configure_argument_parser(parser):
            parser.add_argument('test', help='test argument')

        self.script.configure_argument_parser = configure_argument_parser
        parser = self.script.get_parser()

        fh = StringIO()
        parser.print_help(file=fh)
        self.assertIn('test argument', fh.getvalue())

    def test_create_metrics(self):
        '''Metrics are created based on the configuration.'''
        configs = [
            MetricConfig('m1', 'desc1', 'counter', {}),
            MetricConfig('m2', 'desc2', 'histogram', {})]
        metrics = self.script.create_metrics(configs)
        self.assertEqual(len(metrics), 2)
        self.assertEqual(metrics['m1']._type, 'counter')
        self.assertEqual(metrics['m2']._type, 'histogram')

    def test_invalid_metric_type(self):
        '''An invalid metric type raises an ErrorExitMessage error.'''
        configs = [MetricConfig('m1', 'desc1', 'unknown', {})]
        with self.assertRaises(ErrorExitMessage) as cm:
            self.script.create_metrics(configs)
        self.assertEqual(
            str(cm.exception),
            'Invalid type for m1: must be one of counter, gauge,'
            ' histogram, summary')

    @mock.patch('prometheus_aioexporter.script.setup_logger')
    def test_setup_logging(self, mock_setup_logger):
        '''Logging is set up.'''
        self.script._run_application = lambda *args: None
        self.script([])
        logger_names = (
            'aiohttp.access', 'aiohttp.internal', 'aiohttp.server',
            'aiohttp.web', 'sample-script')
        calls = [
            mock.call(level=logging.WARNING, name=name, stream=mock.ANY)
            for name in logger_names]
        mock_setup_logger.assert_has_calls(calls)

    def test_include_process_stats(self):
        '''The script can include process stats in metrics.'''
        self.script._run_application = lambda *args: None
        self.script(['--process-stats'])
        # process stats are present in the registry
        self.assertIn(
            'process_cpu_seconds_total',
            self.script.registry._names_to_collectors)

    def test_create_application_registers_handlers(self):
        '''Startup/shutdown handlers are registered with the application.'''
        args = self.script.get_parser().parse_args([])
        application = self.script._create_application(args)
        self.assertIn(
            self.script.on_application_startup, application.on_startup)
        self.assertIn(
            self.script.on_application_shutdown, application.on_shutdown)

    @mock.patch('prometheus_aioexporter.script.web.run_app')
    def test_run_application(self, mock_run_app):
        self.script([])
        mock_run_app.assert_called_with(
            mock.ANY, host='localhost', port=9090, print=mock.ANY,
            access_log_format='%a "%r" %s %b "%{Referrer}i" "%{User-Agent}i"')
