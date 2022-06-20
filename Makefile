# all the recipes are phony (no files to check).
.PHONY: .check-env-vars .deps .pip-install docs tests build dev run update install-local run-local deploy help release configure-credentials
.DEFAULT_GOAL := help

IS_LINUX_OS := $(shell uname -s | grep -c Linux)
# IS_POETRY := $(shell command -v poetry  2> /dev/null)
IS_POETRY := $(shell pip freeze | grep "poetry==")
IS_TWINE := $(shell pip freeze | grep "twine==")


export PATH := ${HOME}/.local/bin:$(PATH)

help:
	@echo "Please use 'make <target>' where <target> is one of"
	@echo ""
	@echo "  build                     builds the app in Docker"
	@echo "  run                       runs the app in Docker with prod settings"
	@echo "  dev                       runs the app in Docker with dev settings"
	@echo "  run-local                 runs the app locally with prod settings"
	@echo "  run-local-sudo            runs the app locally using prod settings and root privileges"
	@echo "  poetry-update             updates the dependencies in poetry.lock"
	@echo "  install-local             installs pyslac into the current environment"
	@echo "  tests                     run all the tests"
	@echo "  reformat                  reformats the code, using Black"
	@echo "  flake8                    flakes8 the code"
	@echo "  release version=<mj.mn.p> bumps the project version to <mj.mn.p>, using poetry;"
	@echo ""
	@echo "Check the Makefile to know exactly what each target is doing."

.install-poetry:
	@if [ -z ${IS_POETRY} ]; then pip install poetry; fi

.check-os:
	@# The @ is to supress the output of the evaluation
	@if [ ${IS_LINUX_OS} -eq 0 ]; then echo "This recipe is not available in non-Linux Systems. \
	Please, consider using 'make build' to run the tests in a Docker container"; exit 3; fi

.deps:
	@if [ -z ${IS_POETRY} ]; then pip install poetry; fi
	@if [ -z ${IS_TWINE} ]; then pip install twine; fi

docs:
	# poetry run sphinx-build -b html docs/source docs/build

tests: .check-os
	poetry run pytest -vv tests

build:
	docker-compose build

dev:
	# the dev file apply changes to the original compose file
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

run:
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up

poetry-update:
	poetry update

install-local:
	pip install .

run-local-single:
	python pyslac/examples/single_slac_session.py

run-local-multiple:
	python pyslac/examples/multiple_slac_sessions.py

run-local-sudo-single:
	sudo $(shell which python) pyslac/examples/single_slac_session.py

run-local-sudo-multiple:
	sudo $(shell which python) pyslac/examples/multiple_slac_sessions.py

run-ev-slac:
	sudo $(shell which python) pyslac/examples/ev_slac_scapy.py

mypy:
	mypy --config-file mypy.ini pyslac tests

reformat:
	isort pyslac tests && black --exclude --line-length=88 pyslac tests

black:
	black --exclude --check --diff --line-length=88 pyslac tests

flake8:
	flake8 --config .flake8 pyslac tests

code-quality: reformat mypy black flake8

release: .install-poetry
	@echo "Please remember to update the CHANGELOG.md, before tagging the release"
	@poetry version ${version}

