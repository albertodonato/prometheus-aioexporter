from setuptools import setup, find_packages

from prometheus_aioexporter import __version__, __doc__ as description

config = {
    'name': 'prometheus-aioexporter',
    'version': __version__,
    'license': 'LGPLv3+',
    'description': description,
    'long_description': open('README.rst').read(),
    'author': 'Alberto Donato',
    'author_email': 'alberto.donato@gmail.com',
    'maintainer': 'Alberto Donato',
    'maintainer_email': 'alberto.donato@gmail.com',
    'url': 'https://github.com/albertodonato/prometheus-aioexporter',
    'packages': find_packages(),
    'include_package_data': True,
    'test_suite': 'prometheus_aioexporter',
    'install_requires': [
        'aiohttp',
        'prometheus-client',
        'toolrack'],
    'tests_require': ['asynctest'],
    'keywords': 'prometheus exporter library'}

setup(**config)
