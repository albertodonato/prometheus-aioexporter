from pathlib import Path

from setuptools import (
    find_packages,
    setup,
)

from prometheus_aioexporter import (
    __doc__ as description,
    __version__,
)

tests_require = ['pytest', 'pytest-aiohttp', 'pytest-mock']

config = {
    'name': 'prometheus-aioexporter',
    'version': __version__,
    'license': 'LGPLv3+',
    'description': description,
    'long_description': Path('README.rst').read_text(),
    'author': 'Alberto Donato',
    'author_email': 'alberto.donato@gmail.com',
    'maintainer': 'Alberto Donato',
    'maintainer_email': 'alberto.donato@gmail.com',
    'url': 'https://github.com/albertodonato/prometheus-aioexporter',
    'packages': find_packages(),
    'include_package_data': True,
    'test_suite': 'prometheus_aioexporter',
    'install_requires': [
        'aiohttp >= 3.0.0', 'prometheus-client', 'toolrack >= 2.1.0'
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
