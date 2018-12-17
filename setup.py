from pathlib import Path

from setuptools import (
    find_packages,
    setup,
)

tests_require = ['pytest', 'pytest-aiohttp', 'pytest-mock']

config = {
    'name': 'prometheus-aioexporter',
    'version': '1.5.0',
    'license': 'LGPLv3+',
    'description': 'Asyncio library for creating Prometheus exporters.',
    'long_description': Path('README.rst').read_text(),
    'author': 'Alberto Donato',
    'author_email': 'alberto.donato@gmail.com',
    'maintainer': 'Alberto Donato',
    'maintainer_email': 'alberto.donato@gmail.com',
    'url': 'https://github.com/albertodonato/prometheus-aioexporter',
    'packages': find_packages(include='prometheus_aioexporter.*'),
    'include_package_data': True,
    'test_suite': 'prometheus_aioexporter',
    'install_requires': [
        'aiohttp >= 3.0.0', 'prometheus-client >= 0.4.0', 'toolrack >= 2.1.0'
    ],
    'tests_require': tests_require,
    'extras_require': {
        'testing': tests_require
    },
    'keywords': 'prometheus exporter library',
    'classifiers': [
        'Development Status :: 4 - Beta', 'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        (
            'License :: OSI Approved :: '
            'GNU Lesser General Public License v3 or later (LGPLv3+)'),
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3 :: Only', 'Topic :: Utilities',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ]
}

setup(**config)
