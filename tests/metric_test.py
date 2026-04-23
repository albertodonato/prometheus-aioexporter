import typing as t

from prometheus_client import Histogram
import pytest

from prometheus_aioexporter._metric import (
    InvalidMetricType,
    MetricConfig,
    MetricsRegistry,
)


class TestMetricConfig:
    def test_invalid_metric_type(self) -> None:
        with pytest.raises(InvalidMetricType) as error:
            MetricConfig("m1", "desc1", "unknown")
        assert str(error.value) == (
            "Invalid type for m1: must be one of counter, enum, "
            "gauge, histogram, info, summary"
        )

    def test_labels_sorted(self) -> None:
        config = MetricConfig("m", "desc", "counter", labels=["foo", "bar"])
        assert config.labels == ("bar", "foo")


class TestMetricsRegistry:
    def test_create_metrics(self) -> None:
        configs = [
            MetricConfig("m1", "desc1", "counter"),
            MetricConfig("m2", "desc2", "histogram"),
        ]
        metrics = MetricsRegistry().create_metrics(configs)
        assert len(metrics) == 2
        assert metrics["m1"]._type == "counter"
        assert metrics["m2"]._type == "histogram"

    def test_create_metrics_with_config(self) -> None:
        configs = [
            MetricConfig(
                "m1", "desc1", "histogram", config={"buckets": [10, 20]}
            )
        ]
        metrics = MetricsRegistry().create_metrics(configs)
        # Histogram has the two specified bucket plus +Inf
        histogram = t.cast(Histogram, metrics["m1"])
        assert len(histogram._buckets) == 3

    def test_create_metrics_config_ignores_unknown(self) -> None:
        configs = [
            MetricConfig("m1", "desc1", "gauge", config={"unknown": "value"})
        ]
        metrics = MetricsRegistry().create_metrics(configs)
        assert len(metrics) == 1

    def test_get_metrics(self) -> None:
        registry = MetricsRegistry()
        metrics = registry.create_metrics(
            [
                MetricConfig("metric1", "A test gauge", "gauge"),
                MetricConfig("metric2", "A test histogram", "histogram"),
            ]
        )
        assert registry.get_metrics() == metrics

    def test_get_metric(self) -> None:
        configs = [
            MetricConfig(
                "m",
                "A test gauge",
                "gauge",
                labels=["l1", "l2"],
            )
        ]
        registry = MetricsRegistry()
        registry.create_metrics(configs)
        metric = registry.get_metric("m")
        assert metric._name == "m"
        assert metric._labelvalues == ()

    def test_get_metric_with_labels(self) -> None:
        configs = [
            MetricConfig("m", "A test gauge", "gauge", labels=("l1", "l2"))
        ]
        registry = MetricsRegistry()
        registry.create_metrics(configs)
        metric = registry.get_metric("m", {"l1": "v1", "l2": "v2"})
        assert metric._labelvalues == ("v1", "v2")
