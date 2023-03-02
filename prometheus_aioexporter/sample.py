from argparse import Namespace
import random

from aiohttp.web import Application
from prometheus_client import Metric

from . import (
    MetricConfig,
    PrometheusExporterScript,
)


class SampleScript(PrometheusExporterScript):
    """A sample exporter."""

    name = "prometheus-aioexporter-sample"
    default_port = 9091

    def configure(self, args: Namespace) -> None:
        self.create_metrics(
            [
                MetricConfig("a_gauge", "a gauge", "gauge", {"labels": ["foo", "bar"]}),
                MetricConfig("a_counter", "a counter", "counter", {"labels": ["baz"]}),
            ]
        )

    async def on_application_startup(self, application: Application) -> None:
        application["exporter"].set_metric_update_handler(self._update_handler)

    async def _update_handler(self, metrics: dict[str, Metric]) -> None:
        metrics["a_gauge"].labels(
            foo=random.choice(["this-foo", "other-foo"]),
            bar=random.choice(["this-bar", "other-bar"]),
        ).set(random.uniform(0, 100))
        metrics["a_counter"].labels(
            baz=random.choice(["this-baz", "other-baz"]),
        ).inc(random.choice(range(10)))


script = SampleScript()
