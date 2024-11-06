from argparse import ArgumentParser
from collections.abc import Iterator
from io import StringIO
from ssl import SSLContext
from unittest import mock

import pytest
from pytest_mock import MockerFixture

from prometheus_aioexporter._log import AccessLogger
from prometheus_aioexporter._metric import MetricConfig
from prometheus_aioexporter._script import PrometheusExporterScript


class SampleScript(PrometheusExporterScript):
    """A sample script"""

    name = "sample-script"
    default_port = 12345

    def configure_argument_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument("--test", help="test argument")


@pytest.fixture
def script() -> Iterator[PrometheusExporterScript]:
    yield SampleScript()


@pytest.mark.usefixtures("log")
class TestPrometheusExporterScript:
    def test_description(self, script: PrometheusExporterScript) -> None:
        assert script.description == "A sample script"

    def test_description_empty(self, script: PrometheusExporterScript) -> None:
        script.__doc__ = None
        assert script.description == ""

    def test_configure_argument_parser(
        self, script: PrometheusExporterScript
    ) -> None:
        parser = script.get_parser()

        fh = StringIO()
        parser.print_help(file=fh)
        assert "test argument" in fh.getvalue()

    def test_create_metrics(self, script: PrometheusExporterScript) -> None:
        configs = [
            MetricConfig("m1", "desc1", "counter", {}),
            MetricConfig("m2", "desc2", "histogram", {}),
        ]
        metrics = script.create_metrics(configs)
        assert len(metrics) == 2
        assert metrics["m1"]._type == "counter"
        assert metrics["m2"]._type == "histogram"

    def test_change_metrics_path(
        self, script: PrometheusExporterScript
    ) -> None:
        args = script.get_parser().parse_args(
            ["--metrics-path", "/other-path"]
        )
        exporter = script._get_exporter(args)
        assert exporter.metrics_path == "/other-path"

    def test_only_ssl_key(
        self, script: PrometheusExporterScript, tls_private_key_path: str
    ) -> None:
        args = script.get_parser().parse_args(
            ["--ssl-private-key", tls_private_key_path]
        )
        exporter = script._get_exporter(args)
        assert exporter.ssl_context is None

    def test_only_ssl_cert(
        self, script: PrometheusExporterScript, tls_public_key_path: str
    ) -> None:
        args = script.get_parser().parse_args(
            ["--ssl-public-key", tls_public_key_path]
        )
        exporter = script._get_exporter(args)
        assert exporter.ssl_context is None

    def test_ssl_components_without_ca(
        self,
        script: PrometheusExporterScript,
        tls_private_key_path: str,
        tls_public_key_path: str,
    ) -> None:
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
        self,
        script: PrometheusExporterScript,
        tls_private_key_path: str,
        tls_ca_path: str,
        tls_public_key_path: str,
    ) -> None:
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

    def test_include_process_stats(
        self, mocker: MockerFixture, script: PrometheusExporterScript
    ) -> None:
        mocker.patch("prometheus_aioexporter._web.PrometheusExporter.run")
        script(["--process-stats"])
        # process stats are present in the registry
        assert (
            "process_cpu_seconds_total"
            in script.registry.registry._names_to_collectors
        )

    def test_get_exporter_registers_handlers(
        self, script: PrometheusExporterScript
    ) -> None:
        args = script.get_parser().parse_args([])
        exporter = script._get_exporter(args)
        assert script.on_application_startup in exporter.app.on_startup
        assert script.on_application_shutdown in exporter.app.on_shutdown

    def test_script_run_exporter_ssl(
        self,
        mocker: MockerFixture,
        script: PrometheusExporterScript,
        ssl_context: SSLContext,
        tls_private_key_path: str,
        tls_public_key_path: str,
    ) -> None:
        mock_run_app = mocker.patch("prometheus_aioexporter._web.run_app")
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

    def test_script_run_exporter(
        self, mocker: MockerFixture, script: PrometheusExporterScript
    ) -> None:
        mock_run_app = mocker.patch("prometheus_aioexporter._web.run_app")
        script([])
        mock_run_app.assert_called_with(
            mock.ANY,
            host=["localhost"],
            port=12345,
            print=mock.ANY,
            access_log_class=AccessLogger,
            ssl_context=None,
        )
