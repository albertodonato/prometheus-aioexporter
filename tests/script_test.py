from io import StringIO
import logging
from unittest import mock

from prometheus_aioexporter.metric import MetricConfig
from prometheus_aioexporter.script import PrometheusExporterScript


class SampleScript(PrometheusExporterScript):
    """A sample script"""

    name = "sample-script"
    default_port = 12345


class TestPrometheusExporterScript:
    def test_description(self):
        """The description attribute returns the class docstring."""
        assert SampleScript().description == "A sample script"

    def test_description_empty(self):
        """The description is empty string if no docstring is set."""
        script = SampleScript()
        script.__doc__ = None
        assert script.description == ""

    def test_logger(self):
        """The script logger uses the script name."""
        assert SampleScript().logger.name == "sample-script"

    def test_configure_argument_parser(self):
        """configure_argument_parser adds specified arguments."""

        def configure_argument_parser(parser):
            parser.add_argument("test", help="test argument")

        script = SampleScript()
        script.configure_argument_parser = configure_argument_parser
        parser = script.get_parser()

        fh = StringIO()
        parser.print_help(file=fh)
        assert "test argument" in fh.getvalue()

    def test_create_metrics(self):
        """Metrics are created based on the configuration."""
        configs = [
            MetricConfig("m1", "desc1", "counter", {}),
            MetricConfig("m2", "desc2", "histogram", {}),
        ]
        metrics = SampleScript().create_metrics(configs)
        assert len(metrics) == 2
        assert metrics["m1"]._type == "counter"
        assert metrics["m2"]._type == "histogram"

    def test_setup_logging(self, mocker):
        """Logging is set up."""
        mock_setup_logger = mocker.patch("prometheus_aioexporter.script.setup_logger")
        mocker.patch("prometheus_aioexporter.web.PrometheusExporter.run")
        SampleScript()([])
        logger_names = (
            "aiohttp.access",
            "aiohttp.internal",
            "aiohttp.server",
            "aiohttp.web",
            "sample-script",
        )
        calls = [
            mock.call(level=logging.WARNING, name=name, stream=mock.ANY)
            for name in logger_names
        ]
        mock_setup_logger.assert_has_calls(calls)

    def test_change_metrics_path(self, mocker):
        """The path under which metrics are exposed can be changed."""
        script = SampleScript()
        args = script.get_parser().parse_args(["--metrics-path", "/other-path"])
        exporter = script._get_exporter(args)
        assert exporter.metrics_path == "/other-path"

    def test_include_process_stats(self, mocker):
        """The script can include process stats in metrics."""
        mocker.patch("prometheus_aioexporter.web.PrometheusExporter.run")
        script = SampleScript()
        script(["--process-stats"])
        # process stats are present in the registry
        assert (
            "process_cpu_seconds_total" in script.registry.registry._names_to_collectors
        )

    def test_get_exporter_registers_handlers(self):
        """Startup/shutdown handlers are registered with the application."""
        script = SampleScript()
        args = script.get_parser().parse_args([])
        exporter = script._get_exporter(args)
        assert script.on_application_startup in exporter.app.on_startup
        assert script.on_application_shutdown in exporter.app.on_shutdown

    def test_script_run_exporter(self, mocker):
        """The script runs the exporter application."""
        mock_run_app = mocker.patch("prometheus_aioexporter.web.run_app")
        SampleScript()([])
        mock_run_app.assert_called_with(
            mock.ANY,
            host=["localhost"],
            port=12345,
            print=mock.ANY,
            access_log_format='%a "%r" %s %b "%{Referrer}i" "%{User-Agent}i"',
        )
