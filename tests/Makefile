# all the recipes are phony (no files to check).
.PHONY: .check-env-vars deps docs test build dev run update install-local run-local deploy


export PATH := ${HOME}/.local/bin:$(PATH)

.check-env-vars:
	@test $${PYPI_USER?Please set environment variable PYPI_USER}
	@test $${PYPI_PASS?Please set environment variable PYPI_PASS}

deps:
	pip install poetry

docs:
	# poetry run sphinx-build -b html docs/source docs/build

test:
	#poetry run flake8 pytest -vv tests
	poetry run pytest -vv tests

build: .check-env-vars
	docker-compose build

dev: .check-env-vars
    # the dev file apply changes to the original compose file
	docker-compose -f ../docker-compose.yml -f ../docker-compose.dev.yml up

run: build
	docker-compose up

poetry-config: .check-env-vars
	# For external packages, poetry saves metadata
	# in it's cache which can raise versioning problems, if the package
	# suffered version support changes. Thus, we clean poetry cache
	yes | poetry cache clear --all mqtt_api
	poetry config http-basic.pypi-switch ${PYPI_USER} ${PYPI_PASS}

poetry-update: poetry-config
	poetry update

poetry-install: poetry-update
	poetry install

run-local:
	python slac/main.py

mypy:
	mypy --config-file ../mypy.ini slac tests

reformat:
	isort slac tests && black --line-length=88 slac tests

black:
	black --check --diff --line-length=88 slac tests

flake8:
	flake8 --config ../.flake8 slac tests

code-quality: reformat mypy black flake8

deploy: deps build
	# twine upload dist/*.tar.gz
