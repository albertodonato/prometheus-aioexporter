PYTHON = python3
SETUP = $(PYTHON) setup.py


build:
	$(SETUP) build

devel:
	$(SETUP) develop

clean:
	rm -rf build *.egg-info
	find . -type d -name __pycache__ | xargs rm -rf

test:
	@$(PYTHON) -m unittest

coverage:
	@coverage run -m unittest
	@coverage report --show-missing --skip-covered --fail-under=100 \
		--include=prometheus_aioexporter/\* --omit=\*\*/tests/\*

lint:
	@flake8 setup.py prometheus_aioexporter

.PHONY: build devel clean test coverage lint
