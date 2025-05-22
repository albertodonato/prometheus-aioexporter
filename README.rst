Asyncio library for creating Prometheus exporters
=================================================

|Latest Version| |Build Status|

``prometheus-aioexporter`` is an aysncio-based library to simplify writing
Prometheus_ exporters in Python.

Exporters are usually implemented as small daemons that expose metrics
in text format through a web endpoint (usually ``/metrics``).


Usage
-----

The library provides a ``PrometheusExporterScript`` class that serves as an
entry point to create services that export Prometheus metrics via an HTTP(s)
endpoint.

Creating a new exporter is just a matter of subclassing
``PrometheusExporterScript`` and implementing a few methods as needed.

An example usage is the following:

.. code:: python

    import click
    from prometheus_aioexporter import Arguments, PrometheusExporterScript


    class MyExporter(PrometheusExporterScript):
        """My Prometheus exporter."""

        name = "my-exporter"
        default_port = 9091
        envvar_prefix = "MYEXP"

        def command_line_parameters(self) -> list[click.Parameter]:
            # Additional options for the script
            return [
                click.Option(["--custom-option"], help="a custom option"),
                ...
            ]

        def configure(self, args: Arguments) -> None:
            # Save attributes that are needed for later
            self.data = do_stuff()
            # ...

        async def on_application_startup(
            self, application: aiohttp.web.Application
        ) -> None:
            # Start other asyncio tasks at application startup
            do_something_with(self.data)
            # ...

        async def on_application_shutdown(
            self, application: aiohttp.web.Application
        ) -> None:
            # Stop other asyncio tasks at application shutdown
            do_more_with(self.data)
            # ...


    script = MyExporter()


Also see the `sample script`_ for a complete example.

The ``script`` variable from the example above can be referenced in
``pyproject.toml`` to generate the script, like

.. code:: toml

    [project.scripts]
    my-exporter = "path.to.script:script"


The ``description`` of the exporter can be customized by setting the docstring
in the script class.


Exporter command-line
~~~~~~~~~~~~~~~~~~~~~

``PrometheusExporterScript`` provides a few command-line arguments by default:

.. code::

    Options:
      -H, --host TEXT                 host addresses to bind  [env var: EXP_HOST;
                                      default: localhost]
      -p, --port INTEGER              port to run the webserver on  [env var:
                                      EXP_PORT; default: 9091]
      --metrics-path TEXT             path under which metrics are exposed  [env
                                      var: EXP_METRICS_PATH; default: /metrics]
      -L, --log-level [critical|error|warning|info|debug]
                                      minimum level for log messages  [env var:
                                      EXP_LOG_LEVEL; default: info]
      --log-format [plain|json]       log output format  [env var: EXP_LOG_FORMAT;
                                      default: plain]
      --process-stats                 include process stats in metrics  [env var:
                                      EXP_PROCESS_STATS]
      --ssl-private-key FILE          full path to the ssl private key  [env var:
                                      EXP_SSL_PRIVATE_KEY]
      --ssl-public-key FILE           full path to the ssl public key  [env var:
                                      EXP_SSL_PUBLIC_KEY]
      --ssl-ca FILE                   full path to the ssl certificate authority
                                      (CA)  [env var: EXP_SSL_CA]
      --version                       Show the version and exit.
      --help                          Show this message and exit.


Further options can be added by implementing ``command_line_parameters()`` to
return additional ``click.Argument`` and ``click.Option`` items to add to the
command line.

See the Click_ manual for more details on available parameter types.

In order to serve metrics on the HTTPS endpoint both ``ssl-private-key`` and
``ssl-public-key`` need to be define. The ssl certificate authority
(i.e. ``ssl-ca``) is optional.


Environment variables
~~~~~~~~~~~~~~~~~~~~~

Values from default arguments can also be supplied via environment variables.
Variables names match the ``<envvar_prefix>_<option_with_underscores`` format,
so, for instance, the ``--port`` option can be provided as ``MYEXP_PORT=9091``
(assuming the ``PrometheusExporterScript.envvar_prefix`` is set to ``MYEXP``).

Provided command-line options take precedence over environment variables.

It's also possible to provide environment variables via dotenv file. By default
``.env`` is looked up in the current working directory. The file to load can be
overridden by setting the file path via the ``<envvar_prefix>_DOTENV``
variable.

Explicitly provided environment variables take precedence over the ones defined
in the dotenv file.


Startup configuration
~~~~~~~~~~~~~~~~~~~~~

Additional initial setup (e.g. config file parsing) can be performed by the
script by implementing the ``configure()``. This is called at startup with the
parsed arguments (an ``Arguments`` instance).


Metrics configuration
~~~~~~~~~~~~~~~~~~~~~

The metrics exported by the script can be set up by calling ``create_metrics``
with a list of ``MetricConfig``\s. This is typically done in ``configure()``:

.. code:: python

    def configure(self, args: Arguments) -> None:
        # ...
        self.create_metrics(
            [
                MetricConfig("metric1", "a metric", "gauge"),
                MetricConfig("metric2", "another metric", "counter", labels=("l1", "l2")),
            ]
        )


Web application setup
~~~~~~~~~~~~~~~~~~~~~

On startup, ``PrometheusExporterScript`` creates a ``PrometheusExporter`` which
includes a web application that exposes metrics.

It's possible to customize and perform additional startup/shutdown tasks by
implementing the ``on_application_startup`` and ``on_application_shutdown``
coroutine methods, which are called with the application as parameter.

The ``PrometheusExporter`` instance is accessible via
``application[EXPORTER_APP_KEY]``), and provides a ``set_metric_update_handler``
method to register a hook to update metrics on each request, before the
response is returned to the client.  The registered function must return a
coroutine and is called with a dict mapping metric names to metric objects:

.. code:: python

    async def on_application_startup(self, application: aiohttp.web.Application) -> None:
        # ...
        application[EXPORTER_APP_KEY].set_metric_update_handler(self._update_handler)

    async def _update_handler(self, metrics: dict[str, prometheus_client.metrics.MetricWrapperBase]):
        for name, metric in metrics.items():
            metric.set(...)


See ``prometheus_aioexporter.sample`` for a complete example (the script can be
run as ``prometheus-aioexporter-sample``).


.. _Prometheus: https://prometheus.io/
.. _Click: https://click.palletsprojects.com/en/stable/
.. _sample script: ./prometheus_aioexporter/sample.py

.. |Latest Version| image:: https://img.shields.io/pypi/v/prometheus-aioexporter.svg
   :alt: Latest Version
   :target: https://pypi.python.org/pypi/prometheus-aioexporter
.. |Build Status| image:: https://github.com/albertodonato/prometheus-aioexporter/workflows/CI/badge.svg
   :alt: Build Status
   :target: https://github.com/albertodonato/prometheus-aioexporter/actions?query=workflow%3ACI
