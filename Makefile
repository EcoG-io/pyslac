# all the recipes are phony (no files to check).
.PHONY: .check-env-vars .deps .pip-install docs tests build dev run update install-local run-local deploy help configure-credentials
.DEFAULT_GOAL := help

IS_LINUX_OS := $(shell uname -s | grep -c Linux)
# IS_POETRY := $(shell command -v poetry  2> /dev/null)
IS_POETRY := $(shell pip freeze | grep "poetry==")
IS_TWINE := $(shell pip freeze | grep "twine==")


export PATH := ${HOME}/.local/bin:$(PATH)

help:
	@echo "Please use 'make <target>' where <target> is one of"
	@echo ""
	@echo "  build             builds the app in Docker"
	@echo "  run               runs the app in Docker with prod settings"
	@echo "  dev               runs the app in Docker with dev settings"
	@echo "  run-local         runs the app locally with prod settings"
	@echo "  run-local-sudo    runs the app locally using prod settings and root privileges"
	@echo "  poetry-update     updates the dependencies in poetry.lock"
	@echo "  install-local     installs slac into the current environment"
	@echo "  set-credentials   sets the Switch PyPi credentials directly into pyroject.toml. Use this recipe with caution"
	@echo "  tests             run all the tests"
	@echo "  reformat          reformats the code, using Black"
	@echo "  flake8            flakes8 the code"
	@echo "  deploy            deploys the project using Poetry (not recommended, only use if really needed)"
	@echo ""
	@echo "Check the Makefile to know exactly what each target is doing."


.check-os:
	# The @ is to surpress the output of the evaluation
	@if [ ${IS_LINUX_OS} -eq 0 ]; then echo "This Recipe is not available in non-Linux Systems"; exit 3; fi

.check-env-vars:
	@test $${PYPI_USER?Please set environment variable PYPI_USER}
	@test $${PYPI_PASS?Please set environment variable PYPI_PASS}

.deps:
	@if [ -z ${IS_POETRY} ]; then pip install poetry; fi
	@if [ -z ${IS_TWINE} ]; then pip install twine; fi

docs:
	# poetry run sphinx-build -b html docs/source docs/build

tests: .check-os
	poetry run pytest -vv tests

build: .check-env-vars
	docker-compose build

dev: .check-env-vars
    # the dev file apply changes to the original compose file
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

run: .check-env-vars
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up

poetry-config: .check-env-vars
	@# For external packages, poetry saves metadata
	@# in it's cache which can raise versioning problems, if the package
	@# suffered version support changes. Thus, we clean poetry cache
	yes | poetry cache clear --all mqtt_api
	sed -i.bkp 's@<username>:<password>@${PYPI_USER}:${PYPI_PASS}@g' pyproject.toml
	poetry config http-basic.pypi-switch ${PYPI_USER} ${PYPI_PASS}

set-credentials: .check-env-vars
	@# Due to a Keyring issue under Ubuntu systems, the password configuration does not work as expected: https://github.com/python-poetry/poetry/issues/4902
	@# As so, instead we use sed to substitute the credentials.
	sed -i.bkp 's@https://pypi.switch-ev.com/simple/@https://${PYPI_USER}:${PYPI_PASS}\@pypi.switch-ev.com/simple/@g' pyproject.toml

poetry-update: poetry-config
	poetry update

.pip-install: poetry-update
	pip install . --extra-index-url https://$PYPI_USER:$PYPI_PASS@pypi.switch-ev.com/simple

install-local: .pip-install

run-local:
	python slac/main.py

run-local-sudo:
	sudo $(shell which python) slac/main.py

run-ev-slac:
	sudo $(shell which python) slac/examples/ev_slac_scapy.py

mypy:
	mypy --config-file mypy.ini slac tests

reformat:
	isort slac tests && black --exclude --line-length=88 slac tests

black:
	black --exclude --check --diff --line-length=88 slac tests

flake8:
	flake8 --config .flake8 slac tests

code-quality: reformat mypy black flake8

bump-version:
	poetry version

deploy: .check-env-vars .deps build bump-version
	poetry config repo.pypi-switch https://pypi.switch-ev.com/
	poetry config http-basic.pypi-switch ${PYPI_USER} ${PYPI_PASS}
	poetry publish -r pypi-switch
