.PHONY: start stop airbyte-install test

AIRBYTE_INSTALL_ARGS ?= --no-browser
PYTHON ?= $(if $(wildcard venv/bin/python),venv/bin/python,python3)

# first setup/upgrade only;
airbyte-install:
	abctl local install $(AIRBYTE_INSTALL_ARGS)

start:
	bash scripts/start.sh

stop:
	bash scripts/stop.sh

test:
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py' -v
