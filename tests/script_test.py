import logging
from io import StringIO
from ssl import SSLContext
from unittest import mock

import pytest

from prometheus_aioexporter.metric import MetricConfig
from prometheus_aioexporter.script import PrometheusExporterScript


class SampleScript(PrometheusExporterScript):
    """A sample script"""

    name = "sample-script"
    default_port = 12345


@pytest.fixture
def script():
    yield SampleScript()


class TestPrometheusExporterScript:
    def test_description(self, script):
        """The description attribute returns the class docstring."""
        assert script.description == "A sample script"

    def test_description_empty(self, script):
        """The description is empty string if no docstring is set."""
        script.__doc__ = None
        assert script.description == ""

    def test_logger(self, script):
        """The script logger uses the script name."""
        assert script.logger.name == "sample-script"

    def test_configure_argument_parser(self, script):
        """configure_argument_parser adds specified arguments."""

        def configure_argument_parser(parser):
            parser.add_argument("test", help="test argument")

        script.configure_argument_parser = configure_argument_parser
        parser = script.get_parser()

        fh = StringIO()
        parser.print_help(file=fh)
        assert "test argument" in fh.getvalue()

    def test_create_metrics(self, script):
        """Metrics are created based on the configuration."""
        configs = [
            MetricConfig("m1", "desc1", "counter", {}),
            MetricConfig("m2", "desc2", "histogram", {}),
        ]
        metrics = script.create_metrics(configs)
        assert len(metrics) == 2
        assert metrics["m1"]._type == "counter"
        assert metrics["m2"]._type == "histogram"

    def test_setup_logging(self, mocker, script):
        """Logging is set up."""
        mock_setup_logger = mocker.patch(
            "prometheus_aioexporter.script.setup_logger"
        )
        mocker.patch("prometheus_aioexporter.web.PrometheusExporter.run")
        script([])
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

    def test_change_metrics_path(self, script):
        """The path under which metrics are exposed can be changed."""
        args = script.get_parser().parse_args(
            ["--metrics-path", "/other-path"]
        )
        exporter = script._get_exporter(args)
        assert exporter.metrics_path == "/other-path"

    def test_only_ssl_key(self, script, tls_private_key_path):
        """The path under which metrics are exposed can be changed."""
        args = script.get_parser().parse_args(
            ["--ssl-private-key", tls_private_key_path]
        )
        exporter = script._get_exporter(args)
        assert exporter.ssl_context is None

    def test_only_ssl_cert(self, script, tls_public_key_path):
        """The path under which metrics are exposed can be changed."""
        args = script.get_parser().parse_args(
            ["--ssl-public-key", tls_public_key_path]
        )
        exporter = script._get_exporter(args)
        assert exporter.ssl_context is None

    def test_ssl_components_without_ca(
        self, script, tls_private_key_path, tls_public_key_path
    ):
        """The path under which metrics are exposed can be changed."""
        args = script.get_parser().parse_args(
            [
                "--ssl-public-key",
                tls_public_key_path,
                "--ssl-private-key",
                tls_private_key_path,
            ]
        )
        exporter = script._get_exporter(args)
        assert isinstance(exporter.ssl_context, SSLContext)
        assert len(exporter.ssl_context.get_ca_certs()) != 1

    def test_ssl_components(
        self, script, tls_private_key_path, tls_ca_path, tls_public_key_path
    ):
        """The path under which metrics are exposed can be changed."""
        args = script.get_parser().parse_args(
            [
                "--ssl-public-key",
                tls_public_key_path,
                "--ssl-private-key",
                tls_private_key_path,
                "--ssl-ca",
                tls_ca_path,
            ]
        )
        exporter = script._get_exporter(args)
        assert isinstance(exporter.ssl_context, SSLContext)
        assert len(exporter.ssl_context.get_ca_certs()) == 1

    def test_include_process_stats(self, mocker, script):
        """The script can include process stats in metrics."""
        mocker.patch("prometheus_aioexporter.web.PrometheusExporter.run")
        script(["--process-stats"])
        # process stats are present in the registry
        assert (
            "process_cpu_seconds_total"
            in script.registry.registry._names_to_collectors
        )

    def test_get_exporter_registers_handlers(self, script):
        """Startup/shutdown handlers are registered with the application."""
        args = script.get_parser().parse_args([])
        exporter = script._get_exporter(args)
        assert script.on_application_startup in exporter.app.on_startup
        assert script.on_application_shutdown in exporter.app.on_shutdown

    def test_script_run_exporter_ssl(
        self,
        mocker,
        script,
        ssl_context,
        tls_private_key_path,
        tls_public_key_path,
    ):
        """The script runs the exporter application."""
        mock_run_app = mocker.patch("prometheus_aioexporter.web.run_app")
        script(
            [
                "--ssl-public-key",
                tls_public_key_path,
                "--ssl-private-key",
                tls_private_key_path,
            ]
        )

        assert isinstance(
            mock_run_app.call_args.kwargs["ssl_context"], SSLContext
        )

    def test_script_run_exporter(self, mocker, script):
        """The script runs the exporter application."""
        mock_run_app = mocker.patch("prometheus_aioexporter.web.run_app")
        script([])
        mock_run_app.assert_called_with(
            mock.ANY,
            host=["localhost"],
            port=12345,
            print=mock.ANY,
            access_log_format='%a "%r" %s %b "%{Referrer}i" "%{User-Agent}i"',
            ssl_context=None,
        )
