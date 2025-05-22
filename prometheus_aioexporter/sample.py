import random
import typing as t

from aiohttp.web import Application
from prometheus_client import (
    Counter,
    Gauge,
)
from prometheus_client.metrics import MetricWrapperBase

from . import (
    EXPORTER_APP_KEY,
    Arguments,
    MetricConfig,
    PrometheusExporterScript,
)


class SampleScript(PrometheusExporterScript):
    """A sample exporter."""

    name = "prometheus-aioexporter-sample"
    default_port = 9091

    def configure(self, args: Arguments) -> None:
        self.create_metrics(
            [
                MetricConfig(
                    "a_gauge", "a gauge", "gauge", labels=("foo", "bar")
                ),
                MetricConfig(
                    "a_counter", "a counter", "counter", labels=("baz",)
                ),
            ]
        )

    async def on_application_startup(self, application: Application) -> None:
        application[EXPORTER_APP_KEY].set_metric_update_handler(
            self._update_handler
        )

    async def _update_handler(
        self, metrics: dict[str, MetricWrapperBase]
    ) -> None:
        gauge = t.cast(Gauge, metrics["a_gauge"])
        gauge.labels(
            foo=random.choice(["this-foo", "other-foo"]),
            bar=random.choice(["this-bar", "other-bar"]),
        ).set(random.uniform(0, 100))
        counter = t.cast(Counter, metrics["a_counter"])
        counter.labels(
            baz=random.choice(["this-baz", "other-baz"]),
        ).inc(random.choice(range(10)))


script = SampleScript()
