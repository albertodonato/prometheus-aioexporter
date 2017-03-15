# v0.2.2 - 2017-03-04

* Add support to provide an update handler at every request with
  `PrometheusExporterApplication.set_metric_update_handler`.
* Add `get_registry_metrics` utility to return metrics for a registry.


# v0.2.1 - 2017-02-28

* Readd `PrometheusExporterScript.create_metrics`.
* Fix lint issues.


# v0.2.0 - 2017-02-28

* Add `PrometheusExporterScript.logger` property.
* Move metric type validation in `MetricConfig` and drop
  `PrometheusExporterScript.create_metrics` method.


# v0.1.0 - 2017-02-26
    
* First release.
