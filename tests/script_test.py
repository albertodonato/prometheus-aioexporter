from collections.abc import Callable, Iterator
from importlib.metadata import PackageNotFoundError
from pathlib import Path
from ssl import SSLContext
from textwrap import dedent
import typing as t
from unittest import mock

import click
from click.testing import CliRunner, Result
import pytest
from pytest_mock import MockerFixture
from pytest_structlog import StructuredLogCapture

from prometheus_aioexporter._log import AccessLogger, LogFormat, LogLevel
from prometheus_aioexporter._metric import MetricConfig
from prometheus_aioexporter._script import Arguments, PrometheusExporterScript


class SampleScript(PrometheusExporterScript):
    """A sample script"""

    name = "sample-script"
    default_port = 12345
    envvar_prefix = "SAMPLE"

    def command_line_parameters(self) -> list[click.Parameter]:
        return [
            click.Option(["--test"], help="test argument", is_flag=True),
        ]


@pytest.fixture
def make_arguments() -> Iterator[Callable[..., Arguments]]:
    def make(**kwargs: t.Any) -> Arguments:
        args = {
            "host": ("localhost",),
            "port": 9090,
            "metrics_path": "/metrics",
            "log_level": LogLevel.INFO,
            "log_format": LogFormat.PLAIN,
            "process_stats": False,
            "ssl_private_key": None,
            "ssl_public_key": None,
            "ssl_ca": None,
        }
        return Arguments(**(args | kwargs))

    yield make


@pytest.fixture
def mock_run_app(mocker: MockerFixture) -> Iterator[mock.MagicMock]:
    yield mocker.patch("prometheus_aioexporter._web.run_app")


@pytest.fixture
def script(mock_run_app: mock.MagicMock) -> Iterator[PrometheusExporterScript]:
    yield SampleScript()


@pytest.fixture
def invoke_cli(
    script: PrometheusExporterScript,
) -> Iterator[Callable[..., Result]]:
    def invoke(*args: str) -> Result:
        return CliRunner().invoke(script.command, args)

    yield invoke


@pytest.fixture
def parse_arguments(
    monkeypatch: pytest.MonkeyPatch,
    mocker: MockerFixture,
    script: PrometheusExporterScript,
    invoke_cli: Callable[..., Result],
) -> Iterator[Callable[..., Arguments]]:
    accumulate = []

    def execute(args: Arguments) -> None:
        accumulate.append(args)

    mocker.patch.object(script, "_execute", execute)
    monkeypatch.setattr("os.environ", {})

    def invoke(*args: str) -> Arguments:
        script._process_dotenv()
        result = invoke_cli(*args)
        assert result.exit_code == 0
        return accumulate.pop()

    yield invoke


class TestArguments:
    def test_repr(self) -> None:
        assert (
            repr(Arguments(foo="bar", baz=99))
            == "Arguments(baz=99, foo='bar')"
        )

    @pytest.mark.parametrize(
        "other,equal",
        [
            (Arguments(foo="bar", baz=99), True),
            (Arguments(foo="other", baz=99), False),
            (Arguments(foo="bar", other=False), False),
        ],
    )
    def test_eq(self, other: Arguments, equal: bool) -> None:
        assert (Arguments(foo="bar", baz=99) == other) is equal

    def test_eq_other_type(self) -> None:
        assert Arguments(foo="bar", baz=99) != object()

    def test_attrs(self) -> None:
        args = Arguments(foo="bar", baz=99)
        assert args.foo == "bar"
        assert args.baz == 99

    def test_attr_not_found(self) -> None:
        args = Arguments(foo="bar", baz=99)
        with pytest.raises(AttributeError) as err:
            args.unknown
        assert str(err.value) == "'Arguments' has no attribute 'unknown'"

    def test_dict(self) -> None:
        assert Arguments(foo="bar", baz=99).dict() == {"foo": "bar", "baz": 99}


@pytest.mark.usefixtures("log")
class TestPrometheusExporterScript:
    def test_version_set(self) -> None:
        class Script(PrometheusExporterScript):
            version = "1.2.3"

        assert Script()._version == "1.2.3"

    def test_version_detected(self, mocker: MockerFixture) -> None:
        mocker.patch(
            "importlib.metadata.version",
            return_value="1.2.3",
        )

        class Script(PrometheusExporterScript): ...

        assert Script()._version == "1.2.3"

    def test_version_unknown(self, mocker: MockerFixture) -> None:
        mocker.patch(
            "importlib.metadata.version",
            side_effect=PackageNotFoundError,
        )
        script = PrometheusExporterScript()
        assert script._version == "unknown"

    def test_description(self, script: PrometheusExporterScript) -> None:
        assert script.description == "A sample script"

    def test_description_empty(self, script: PrometheusExporterScript) -> None:
        script.__doc__ = None
        assert script.description == ""

    def test_default_command_line_paramaters(self) -> None:
        script = PrometheusExporterScript()
        result = CliRunner().invoke(script.command, ["--help"])
        assert result.exit_code == 0
        assert "--host" in result.output
        assert "--port" in result.output

    def test_command_line_parameters(
        self, invoke_cli: Callable[..., Result]
    ) -> None:
        result = invoke_cli("--help")
        assert result.exit_code == 0
        assert "--test" in result.output
        assert "test argument" in result.output

    def test_arguments_defaults(
        self,
        make_arguments: Callable[..., Arguments],
        parse_arguments: Callable[..., Arguments],
    ) -> None:
        assert parse_arguments() == make_arguments(port=12345, test=False)

    def test_arguments_from_cli_builtins(
        self,
        make_arguments: Callable[..., Arguments],
        parse_arguments: Callable[..., Arguments],
    ) -> None:
        args = parse_arguments(
            "--process-stats",
            "--log-format",
            "json",
            "--log-level",
            "debug",
        )
        assert args.process_stats
        assert args.log_format == LogFormat.JSON
        assert args.log_level == LogLevel.DEBUG

    def test_arguments_from_cli(
        self,
        make_arguments: Callable[..., Arguments],
        parse_arguments: Callable[..., Arguments],
    ) -> None:
        assert parse_arguments("--port", "9999", "--test") == make_arguments(
            port=9999, test=True
        )

    def test_arguments_from_env(
        self,
        monkeypatch: pytest.MonkeyPatch,
        make_arguments: Callable[..., Arguments],
        parse_arguments: Callable[..., Arguments],
    ) -> None:
        monkeypatch.setenv("SAMPLE_PORT", "9999")
        monkeypatch.setenv("SAMPLE_TEST", "true")
        assert parse_arguments() == make_arguments(port=9999, test=True)

    def test_arguments_from_cli_precedence_over_env(
        self,
        monkeypatch: pytest.MonkeyPatch,
        make_arguments: Callable[..., Arguments],
        parse_arguments: Callable[..., Arguments],
    ) -> None:
        monkeypatch.setenv("SAMPLE_PORT", "1234")
        monkeypatch.setenv("SAMPLE_TEST", "false")
        assert parse_arguments("--port", "9999", "--test") == make_arguments(
            port=9999, test=True
        )

    def test_arguments_from_dotenv(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        make_arguments: Callable[..., Arguments],
        parse_arguments: Callable[..., Arguments],
    ) -> None:
        dotenv_file = tmp_path / "dotenv"
        monkeypatch.setenv("SAMPLE_DOTENV", str(dotenv_file))
        dotenv_file.write_text(
            dedent(
                """\
                SAMPLE_PORT=9999
                SAMPLE_TEST=true
                """
            )
        )
        assert parse_arguments() == make_arguments(port=9999, test=True)

    def test_arguments_from_env_precedence_over_dotenv(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        make_arguments: Callable[..., Arguments],
        parse_arguments: Callable[..., Arguments],
    ) -> None:
        dotenv_file = tmp_path / "dotenv"
        monkeypatch.setenv("SAMPLE_PORT", "9999")
        monkeypatch.setenv("SAMPLE_TEST", "true")
        monkeypatch.setenv("SAMPLE_DOTENV", str(dotenv_file))
        dotenv_file.write_text(
            dedent(
                """\
                SAMPLE_PORT=1234
                SAMPLE_TEST=false
                """
            )
        )
        assert parse_arguments() == make_arguments(port=9999, test=True)

    def test_call(
        self,
        script: PrometheusExporterScript,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        with pytest.raises(SystemExit):
            script("--help")
        captured = capsys.readouterr()
        assert "--help" in captured.out

    def test_execute_error(
        self,
        mocker: MockerFixture,
        log: StructuredLogCapture,
        script: PrometheusExporterScript,
        invoke_cli: Callable[..., Result],
    ) -> None:
        error = Exception("boom!")
        mocker.patch.object(script, "_execute", side_effect=error)
        result = invoke_cli()
        assert result.exit_code == 1
        assert log.has("exception", exception=error)

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
        self,
        script: PrometheusExporterScript,
        make_arguments: Callable[..., Arguments],
    ) -> None:
        args = make_arguments(metrics_path="/other-path")
        exporter = script._get_exporter(args)
        assert exporter.metrics_path == "/other-path"

    def test_only_ssl_key(
        self,
        script: PrometheusExporterScript,
        make_arguments: Callable[..., Arguments],
        tls_private_key_path: str,
    ) -> None:
        args = make_arguments(ssl_private_key=tls_private_key_path)
        exporter = script._get_exporter(args)
        assert exporter.ssl_context is None

    def test_only_ssl_cert(
        self,
        script: PrometheusExporterScript,
        make_arguments: Callable[..., Arguments],
        tls_public_key_path: str,
    ) -> None:
        args = make_arguments(ssl_public_key=tls_public_key_path)
        exporter = script._get_exporter(args)
        assert exporter.ssl_context is None

    def test_ssl_components_without_ca(
        self,
        script: PrometheusExporterScript,
        make_arguments: Callable[..., Arguments],
        tls_private_key_path: str,
        tls_public_key_path: str,
    ) -> None:
        args = make_arguments(
            ssl_public_key=tls_public_key_path,
            ssl_private_key=tls_private_key_path,
        )
        exporter = script._get_exporter(args)
        assert isinstance(exporter.ssl_context, SSLContext)
        assert len(exporter.ssl_context.get_ca_certs()) != 1

    def test_ssl_components(
        self,
        script: PrometheusExporterScript,
        make_arguments: Callable[..., Arguments],
        tls_private_key_path: str,
        tls_ca_path: str,
        tls_public_key_path: str,
    ) -> None:
        args = make_arguments(
            ssl_public_key=tls_public_key_path,
            ssl_private_key=tls_private_key_path,
            ssl_ca=tls_ca_path,
        )
        exporter = script._get_exporter(args)
        assert isinstance(exporter.ssl_context, SSLContext)
        assert len(exporter.ssl_context.get_ca_certs()) == 1

    def test_include_process_stats(
        self,
        script: PrometheusExporterScript,
        invoke_cli: Callable[..., Arguments],
    ) -> None:
        result = invoke_cli("--process-stats")
        assert result.exit_code == 0
        # process stats are present in the registry
        assert (
            "process_cpu_seconds_total"
            in script.registry.registry._names_to_collectors
        )

    def test_get_exporter_registers_handlers(
        self,
        script: PrometheusExporterScript,
        make_arguments: Callable[..., Arguments],
    ) -> None:
        args = make_arguments()
        exporter = script._get_exporter(args)
        assert script.on_application_startup in exporter.app.on_startup
        assert script.on_application_shutdown in exporter.app.on_shutdown

    def test_script_run_exporter_ssl(
        self,
        mock_run_app: mock.MagicMock,
        script: PrometheusExporterScript,
        invoke_cli: Callable[..., Arguments],
        ssl_context: SSLContext,
        tls_private_key_path: str,
        tls_public_key_path: str,
    ) -> None:
        result = invoke_cli(
            "--ssl-public-key",
            tls_public_key_path,
            "--ssl-private-key",
            tls_private_key_path,
        )
        assert result.exit_code == 0

        assert isinstance(
            mock_run_app.call_args.kwargs["ssl_context"], SSLContext
        )

    def test_script_run_exporter(
        self,
        mock_run_app: mock.MagicMock,
        script: PrometheusExporterScript,
        invoke_cli: Callable[..., Arguments],
    ) -> None:
        invoke_cli()
        mock_run_app.assert_called_with(
            mock.ANY,
            host=("localhost",),
            port=12345,
            print=mock.ANY,
            access_log_class=AccessLogger,
            ssl_context=None,
        )
