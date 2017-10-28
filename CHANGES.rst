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
