# Build image
FROM python:3.10.0-buster as build

ARG PYPI_USER
ARG PYPI_PASS

WORKDIR /usr/src/app

ENV PYTHONFAULTHANDLER=1 \
  PYTHONUNBUFFERED=1 \
  PYTHONHASHSEED=random \
  PIP_NO_CACHE_DIR=1 \
  PIP_DISABLE_PIP_VERSION_CHECK=1 \
  PIP_DEFAULT_TIMEOUT=100 \
  POETRY_VERSION=1.1.11 \
  VIRTUALENV_PIP=21.2.1

RUN pip install "poetry==$POETRY_VERSION"

# Due to an issue with Python 3.10 and poetry, if we use a poetry virtual env,
# we need to disable the option: poetry config experimental.new-installer false
# check https://github.com/python-poetry/poetry/issues/4210
# However, if we run poetry config virtualenvs.create false, then we dont.
# Do not create a virtual poetry env as we already are in an isolated container
RUN poetry config virtualenvs.create false
# Set the credentials
RUN poetry config http-basic.pypi-switch $PYPI_USER $PYPI_PASS
# pylintrc, coveragerc, poetry.lock and pyproject.toml shall not change very
# often, so it is a good idea to add them as soon as possible
COPY .coveragerc pyproject.toml poetry.lock ./
# Update the dependencies and install them in the env
RUN poetry update

# Copy the project to the system and install all dependencies
COPY . ./
RUN poetry install --no-interaction --no-ansi
# Run the tests and linting for slac (as we are not using poetry venv, we are
# not running it with RUN poetry run pytest...)
RUN pytest -vv --cov-config .coveragerc --cov-report term-missing  --durations=3 --cov=.
RUN flake8 --config .flake8 slac tests


# Generate the wheel to be used by next stage
RUN poetry build
# Unfortunately, couldnt find a way to generate only compatible wheels with this
# platform, so I had to remove the MacOS .whl for the dir
RUN rm dist/*macosx*


# Runtime image (which is smaller than the build one)
FROM python:3.10.0-buster

WORKDIR /usr/src/app

# create virtualenv
RUN python -m venv /venv

COPY --from=build /usr/src/app/dist/ dist/


# This will install the wheels in the venv
RUN /venv/bin/pip install dist/*.whl
# if it does not work use
# RUN /venv/bin/pip install dist/*.whl --extra-index-url https://$PYPI_USER:$PYPI_PASS@pypi.switch-ev.com/simple

# This will run the entrypoint script defined in the pyproject.toml
CMD /venv/bin/slac