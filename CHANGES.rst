3.1.2 - 2026-02-22
==================

- fix: fix version autodetection
  

3.1.1 - 2026-02-21
==================

- fix: report correct version in log when autodetected
- chore(github): workflows updates and maintenance


3.1.0 - 2025-06-08
==================

- fix: usage of click.Choice with enums
- chore: require Click 8.2 or later
- chore: use AppKey for keying the exporter in the application


3.0.2 - 2025-05-22
==================

- fix: Don't include locals in tracebacks (fixes #9).


3.0.1 - 2024-12-14
==================

- Fix debug message for dotenv file loading.


3.0.0 - 2024-12-13
==================

- Rework ``PrometheusExporterScript`` class, using ``click`` for command line
  parsing.
- Rework logging based on ``structlog``, support structured logging output as
  JSON.
- Support reading configuration options from environment variables.
- Support reading configuration from `.env` file.

**Note**: this version contains incompatible changes with the ``2.x`` series:
- Command-line parsing is now provided by the ``click`` library. To provide
  additional command-line options, the ``command_line_parameters()`` method
  should be implemented, returning a list of ``click.Parameter`` subclasses
  (e.g. ``click.Option`` or ``click.Argument``)
- The ``structlog`` library is used for logging, providing support for
  structured logging. The logger API is essentially backwards compatible with
  the builtin ``logging`` module, with the added ability of passing keyword
  arguments for structured logging.


2.1.0 - 2024-11-20
==================

- Require Python 3.11 or later.
- Switch to ``ruff`` for formatting.


2.0.0 - 2023-10-28
==================

- Add HTTPS (SSL) support.
- Rework ``MetricConfig``, labels are now an attribute.
- Rework project setup, make packages private.
- Add typing to tests.


1.7.0 - 2023-03-02
==================

- Require Python 3.10 or later.
- Rework project setup, move tests.
- Drop ``setup.{py,cfg}``, extract ``tox.ini`` config.


1.6.4 - 2021-11-29
==================

- Drop explicit passing of asyncio loop.
- Update project config.
- Add ``--metrics-path`` option (fixes #4).
- Add ``prometheus-aioexporter-sample`` script.


1.6.3 - 2020-09-13
==================

- Use relative path in metrics link.


1.6.2 - 2019-11-02
==================

- Fix default parameter for ``-H/--host``.
- Convert project formatting to Black.


1.6.1 - 2019-09-17
==================

- Support passing multiple hostnames/addresses to bind via ``-H/--host``.


1.6.0 - 2019-03-26
==================

- Make default exporter port configurable via ``PrometheusExporterScript.default_port``.


1.5.1 - 2018-12-28
==================

- Export ``MetricsRegistry`` and ``MetricConfig`` from package base.
- A few cleanups for Python 3.6


1.5.0 - 2018-12-18
==================

- Support for ``enum`` and ``info`` metric types.
- Support Python 3.7
- Drop support for Python 3.5
- Add typing
- Switch tests to pytest


1.4.0 - 2018-02-20
==================

- Updates to support aiohttp 3.0.x.
- Rename ``PrometheusExporterApplication`` to ``PrometheusExporter``, which
  contains a ``web.Application`` rather than extending it.
- The function passed to
  ``PrometheusExporterScript.on_application_[startup|shutdown]`` must now be
  coroutines.


1.3.0 - 2018-01-20
==================

- The function passed to
  ``PrometheusExporterApplication.set_metric_update_handler`` must now be
  coroutines.


1.2.0 - 2017-10-28
 ==================

- Add ``MetricsRegistry.get_metric`` to return a single metric, possibly
  configured with label values.


1.1.0 - 2017-10-25
==================

- Add ``MetricsRegistry`` to keep track of metrics registered by the
   application.
- Expand documentation and convert to reST.


1.0.2 - 2017-10-15
==================

- Fix error from ``get_registry_metrics`` when the registry has collectors
   without a ``describe()`` method.


1.0.1 - 2017-05-20
==================

- Fix aiohttp warning because of passing loop to the application.


1.0.0 - 2017-05-07
==================

- Update to support aiohttp 2.0.0.


v0.2.2 - 2017-03-04
===================

- Add support to provide an update handler at every request with
   ``PrometheusExporterApplication.set_metric_update_handler``.
- Add ``get_registry_metrics`` utility to return metrics for a registry.


v0.2.1 - 2017-02-28
===================

- Readd ``PrometheusExporterScript.create_metrics``.
- Fix lint issues.


v0.2.0 - 2017-02-28
===================

- Add ``PrometheusExporterScript.logger`` property.
- Move metric type validation in ``MetricConfig`` and drop
   ``PrometheusExporterScript.create_metrics`` method.


v0.1.0 - 2017-02-26
===================

- First release.
