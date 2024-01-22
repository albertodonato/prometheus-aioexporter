Asyncio library for creating Prometheus exporters
=================================================

|Latest Version| |Build Status|

``prometheus-aioexporter`` is an aysncio-based library to simplify writing
Prometheus_ exporters.

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

    from prometheus_aioexporter import PrometheusExporterScript


    class MyExporter(PrometheusExporterScript):
        """My Prometheus exporter."""

        name = "my-exporter"

        def configure_argument_parser(
            self, parser: argparse.ArgumentParser
        ) -> None:
            # Additional arguments to the script
            parser.add_argument("--custom-option", help="a custom option")
            # ...

        def configure(self, args: argparse.Namespace) -> None:
            # Save attributes that are needed for later
            self.data = do_stuff()
            # ...

        async def on_application_startup(
            self, application: aiohttp.web.Application
        ) -> None:
            # Start other asyncio tasks at application startup
            use(self.data)
            # ...

        async def on_application_shutdown(
            self, application: aiohttp.web.Application
        ) -> None:
            # Stop other asyncio tasks at application shutdown
            use(self.data)
            # ...


    script = MyExporter()


Exporter command-line
~~~~~~~~~~~~~~~~~~~~~

``PrometheusExporterScript`` provides a few command-line arguments by default:

.. code::

    optional arguments:
      -h, --help            show this help message and exit
      -H HOST [HOST ...], --host HOST [HOST ...]
                            host addresses to bind (default: ['localhost'])
      -p PORT, --port PORT  port to run the webserver on (default: 9090)
      --metrics-path METRICS_PATH
                            path under which metrics are exposed (default: /metrics)
      -L {CRITICAL,ERROR,WARNING,INFO,DEBUG}, --log-level {CRITICAL,ERROR,WARNING,INFO,DEBUG}
                            minimum level for log messages (default: WARNING)
      --process-stats       include process stats in metrics (default: False)
      --ssl-private-key     full path to the ssl private key
      --ssl-public-key      full path to the ssl public key
      --ssl-ca              full path to the ssl certificate authority (CA)


Further options can be added by implementing ``configure_argument_parser()``,
which receives the ``argparse.ArgumentParser`` instance used by the script.

The ``script`` variable from the example above can be referenced in
``pyproject.toml`` to generate the script, like

.. code:: toml

    [project.scripts]
    my-exporter = "path.to.script:script"


The ``description`` of the exporter can be customized by setting the docstring
in the script class.

In order to serve metrics on the HTTPS endpoint both ``ssl-private-key`` and
``ssl-public-key`` need to be define. The ssl certificate authority
(i.e. ``ssl-ca``) is optional.


Startup configuration
~~~~~~~~~~~~~~~~~~~~~

Additional initial setup (e.g. config file parsing) can be performed by the
script by implementing the ``configure()``. This is called at startup with the
parsed argument (an ``argparse.Namespace`` instance).


Metrics configuration
~~~~~~~~~~~~~~~~~~~~~

The metrics exported by the script can be set up by calling ``create_metrics``
with a list of ``MetricConfig``\s. This is typically done in ``configure()``:

.. code:: python

    def configure(self, args: argparse.Namespace) -> None:
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
``application['exporter']``), and provides a ``set_metric_update_handler``
method to register a hook to update metrics on each request, before the
response is returned to the client.  The registered function must return a
coroutine and is called with a dict mapping metric names to metric objects:

.. code:: python

    async def on_application_startup(self, application: aiohttp.web.Application) -> None:
        # ...
        application["exporter"].set_metric_update_handler(self._update_handler)

    async def _update_handler(self, metrics: dict[str, prometheus_client.metrics.MetricWrapperBase]):
        for name, metric in metrics.items():
            metric.set(...)


See ``prometheus_aioexporter.sample`` for a complete example (the script can be
run as ``prometheus-aioexporter-sample``).


.. _Prometheus: https://prometheus.io/

.. |Latest Version| image:: https://img.shields.io/pypi/v/prometheus-aioexporter.svg
   :alt: Latest Version
   :target: https://pypi.python.org/pypi/prometheus-aioexporter
.. |Build Status| image:: https://github.com/albertodonato/prometheus-aioexporter/workflows/CI/badge.svg
   :alt: Build Status
   :target: https://github.com/albertodonato/prometheus-aioexporter/actions?query=workflow%3ACI
