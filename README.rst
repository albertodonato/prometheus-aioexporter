Asyncio library for creating Prometheus exporters
=================================================

|Latest Version| |Build Status| |Coverage Status|

prometheus-aioexporter is an aysncio-powered library to simplify writing
Prometheus_ exporters.

Exporters are usually implemented as small daemons that expose metrics
in text format through a web endpoint (usually ``/metrics``).


Usage
-----

The library provides a ``PrometheusExporterScript`` class that serves as an
entry point to create services that export Prometheus metrics via an HTTP
endpoint.

Creating a new exporter is just a matter of subclassing
``PrometheusExporterScript`` and implementing a few methods as needed.

An example usage is the following:

.. code:: python

    from prometheus_aioexporter import PrometheusExporterScript


    class MyExporter(PrometheusExporterScript):
        """My Prometheus exporter."""

        def configure_argument_parser(self, parser):
            # Additional arguments to the script
            parser.add_argument("an-option", help="an option")
            # ...

        def configure(self, args):
            # Save attributes that are needed for later
            self.data = do_stuff()
            # ...

        async def on_application_startup(self, application):
            # Start other asyncio tasks at application startup
            use(self.data)
            # ...

        async def on_application_shutdown(self, application):
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


Further options can be added by implementing ``configure_argument_parser()``,
which receives the ``argparse.ArgumentParser`` instance used by the script.

The ``script`` variable from the example above can be referenced in
``setup.cfg`` to generate the script, like

.. code:: ini

   [options.entry_points]
   console_scripts =
       script = path.to.script:script


The ``name`` and ``description`` of the exporter can be customized by setting
the respective attributes in the script class.


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

    def configure(self, args: argparse.Namespace):
        # ...
        self.create_metrics(
            [MetricConfig("metric1", "a metric", "gauge", {}),
             MetricConfig("metric2", "another metric", "counter", {})])


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

    async def on_application_startup(self, application):
        # ...
        application["exporter"].set_metric_update_handler(self._update_handler)

    async def _update_handler(self, metrics):
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
.. |Coverage Status| image:: https://img.shields.io/codecov/c/github/albertodonato/prometheus-aioexporter/master.svg
   :alt: Coverage Status
   :target: https://codecov.io/gh/albertodonato/prometheus-aioexporter
