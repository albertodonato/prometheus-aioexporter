# prometheus-aioexporter - Asyncio library for creating Prometheus exporters

[![Latest Version](https://img.shields.io/pypi/v/prometheus-aioexporter.svg)](https://pypi.python.org/pypi/prometheus-aioexporter)
[![Build Status](https://travis-ci.org/albertodonato/prometheus-aioexporter.svg?branch=master)](https://travis-ci.org/albertodonato/prometheus-aioexporter)
[![Coverage Status](https://codecov.io/gh/albertodonato/prometheus-aioexporter/branch/master/graph/badge.svg)](https://codecov.io/gh/albertodonato/prometheus-aioexporter)

prometheus-aioexporter is an aysncio-powered library that provides a few
utilities to build [Prometheus](https://prometheus.io/) exporters.


## Install

The library can be installed from pip:

```bash
pip install prometheus-aioexporter
```

## Usage

The library provides a `PrometheusExporterScript` class that serves as an entry
point to create services that export Prometheus metrics via an HTTP endpoint.

An example usage is the following:

```python
from prometheus_aioexporter.script import PrometheusExporterScript


class MyExporter(PrometheusExporterScript):
    '''My Prometheus exporter.'''

    def configure_argument_parser(self, parser):
        # Additional arguments to the script
        parser.add_argument('an-option', help='an option')
        ...

    def configure(self, args):
        # Save attributes that are needed for later
        self.data = do_stuff()
        ...
    
    def on_application_startup(self, application):
        # Start other asyncio tasks at application startup
        use(self.data)
        ...

    def on_application_shutdown(self, application):
        # Stop other asyncio tasks at application shutdown
        use(self.data)
        ...
        

script = MyExporter()
```

The `script` variable can be referenced in `setup.py` to generate the script, like

```python
setup(
    ...,
    entry_points={'console_scripts': [script = path.to.script:script']},
    ...)
```

`PrometheusExporterScript` provides the following arguments by default, which can be
exended by implementing `configure_argument_parser()`:


```
optional arguments:
  -h, --help            show this help message and exit
  -H HOST, --host HOST  host address to bind (default: localhost)
  -p PORT, --port PORT  port to run the webserver on (default: 9090)
  -L {CRITICAL,ERROR,WARNING,INFO,DEBUG}, --log-level {CRITICAL,ERROR,WARNING,INFO,DEBUG}
                        minimum level for log messages (default: WARNING)
  --process-stats       include process stats in metrics (default: False)
```
