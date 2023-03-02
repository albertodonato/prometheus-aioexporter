import pytest

from prometheus_aioexporter.metric import (
    InvalidMetricType,
    MetricConfig,
    MetricsRegistry,
)


class TestMetricConfig:
    def test_invalid_metric_type(self):
        """An invalid metric type raises an error."""
        with pytest.raises(InvalidMetricType) as error:
            MetricConfig("m1", "desc1", "unknown", {})
        assert str(error.value) == (
            "Invalid type for m1: must be one of counter, enum, "
            "gauge, histogram, info, summary"
        )


class TestMetricsRegistry:
    def test_create_metrics(self):
        """Prometheus metrics are created from the specified config."""
        configs = [
            MetricConfig("m1", "desc1", "counter", {}),
            MetricConfig("m2", "desc2", "histogram", {}),
        ]
        metrics = MetricsRegistry().create_metrics(configs)
        assert len(metrics) == 2
        assert metrics["m1"]._type == "counter"
        assert metrics["m2"]._type == "histogram"

    def test_create_metrics_with_config(self):
        """Metric configs are applied."""
        configs = [MetricConfig("m1", "desc1", "histogram", {"buckets": [10, 20]})]
        metrics = MetricsRegistry().create_metrics(configs)
        # The two specified bucket plus +Inf
        assert len(metrics["m1"]._buckets) == 3

    def test_create_metrics_config_ignores_unknown(self):
        """Unknown metric configs are ignored and don't cause an error."""
        configs = [MetricConfig("m1", "desc1", "gauge", {"unknown": "value"})]
        metrics = MetricsRegistry().create_metrics(configs)
        assert len(metrics) == 1

    def test_get_metrics(self):
        """get_metrics returns a dict with metrics."""
        registry = MetricsRegistry()
        metrics = registry.create_metrics(
            [
                MetricConfig("metric1", "A test gauge", "gauge", {}),
                MetricConfig("metric2", "A test histogram", "histogram", {}),
            ]
        )
        assert registry.get_metrics() == metrics

    def test_get_metric(self):
        """get_metric returns a metric."""
        configs = [MetricConfig("m", "A test gauge", "gauge", {"labels": ["l1", "l2"]})]
        registry = MetricsRegistry()
        registry.create_metrics(configs)
        metric = registry.get_metric("m")
        assert metric._name == "m"
        assert metric._labelvalues == ()

    def test_get_metric_with_labels(self):
        """get_metric returns a metric configured with labels."""
        configs = [MetricConfig("m", "A test gauge", "gauge", {"labels": ["l1", "l2"]})]
        registry = MetricsRegistry()
        registry.create_metrics(configs)
        metric = registry.get_metric("m", {"l1": "v1", "l2": "v2"})
        assert metric._labelvalues == ("v1", "v2")

    @pytest.mark.parametrize(
        "typ,params,action,text",
        [
            (
                "counter",
                {},
                lambda metric: metric.inc(),
                "counter\ntest_counter_total 1.0",
            ),
            (
                "enum",
                {"states": ["on", "off"]},
                lambda metric: metric.state("on"),
                'test_enum{test_enum="on"}',
            ),
            ("gauge", {}, lambda metric: metric.set(12.3), "test_gauge 12.3"),
            (
                "histogram",
                {"buckets": [10, 20]},
                lambda metric: metric.observe(1.23),
                'test_histogram_bucket{le="10.0"} 1.0',
            ),
            (
                "info",
                {},
                lambda metric: metric.info({"foo": "bar", "baz": "bza"}),
                'test_info_info{baz="bza",foo="bar"}',
            ),
            (
                "summary",
                {},
                lambda metric: metric.observe(1.23),
                "test_summary_sum 1.23",
            ),
        ],
    )
    def test_generate_metrics(self, typ, params, action, text):
        """generate_metrics returns text with metrics values."""
        registry = MetricsRegistry()
        name = "test_" + typ
        metrics = registry.create_metrics(
            [MetricConfig(name, "A test metric", typ, params)]
        )
        action(metrics[name])
        assert text in registry.generate_metrics().decode("utf-8")
