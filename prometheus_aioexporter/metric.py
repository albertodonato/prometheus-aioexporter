from collections import namedtuple

from prometheus_client import Counter, Gauge, Histogram, Summary


# Map metric types to classes and allowed options
METRIC_TYPES = {
    'counter': {
        'class': Counter,
        'options': {
            'labels': 'labelnames'}},
    'gauge': {
        'class': Gauge,
        'options': {
            'labels': 'labelnames'}},
    'histogram': {
        'class': Histogram,
        'options': {
            'labels': 'labelnames',
            'buckets': 'buckets'}},
    'summary': {
        'class': Summary,
        'options': {
            'labels': 'labelnames'}}}


class MetricConfig(namedtuple(
        'MetricConfig', ['name', 'description', 'type', 'config'])):
    '''Configuration for a metric.'''

    def __new__(cls, name, description, typ, config):
        if typ not in METRIC_TYPES:
            raise InvalidMetricType(name, typ)
        return super().__new__(cls, name, description, typ, config)


class InvalidMetricType(Exception):
    '''Raised when invalid metric type is found.'''

    def __init__(self, name, invalid_type):
        self.name = name
        self.invalid_type = invalid_type
        super().__init__(
            'Invalid type for {}: must be one of {}'.format(
                self.name, ', '.join(sorted(METRIC_TYPES))))


def create_metrics(configs, registry):
    '''Create and register Prometheus metrics from a list of MetricConfigs.'''
    return {
        config.name: _register_metric(config, registry)
        for config in configs}


def get_registry_metrics(registry):
    '''Return a dict with metrics to metrics from a CollectorRegistry.'''
    return {
        metric.describe()[0].name: metric
        for metric in registry._collector_to_names}


def _register_metric(config, registry):
    '''Register and return a Prometheus metric.'''
    metric_info = METRIC_TYPES[config.type]
    options = {
        metric_info['options'][key]: value
        for key, value in config.config.items()
        if key in metric_info['options']}
    return metric_info['class'](
        config.name, config.description, registry=registry, **options)
