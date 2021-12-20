# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] - 2021-12-20

### Added

- Makefile recipe to configure the PyPi credentials directly into pyproject.toml, in
  case the usual configuration fails, by @tropxy in https://github.com/SwitchEV/slac/pull/6
- Added Makefile recipe running the EV simulator and to run the project locally
  with super user privileges, by @tropxy in https://github.com/SwitchEV/slac/pull/6

### Removed

- Removed unneeded Timeout setting in `readeth` method, by @tropxy in https://github.com/SwitchEV/slac/pull/6

### Changed

- Changed scapy EV simulator example to a more realistic scenario, by @tropxy in https://github.com/SwitchEV/slac/pull/6
- Changed Makefile recipe for local installation to use pip instead of poetry, by @tropxy in https://github.com/SwitchEV/slac/pull/6
- Updated Readme to be in sync with the code and clearer, by @tropxy in https://github.com/SwitchEV/slac/pull/6

### Fixed

- Env settings configuration, by @tropxy in https://github.com/SwitchEV/slac/pull/6

## [0.3.0] - 2021-11-30

- Added Config by @tropxy in https://github.com/SwitchEV/slac/pull/5

## [0.2.0] - 2021-11-30

### Added

- [#3](https://github.com/SwitchEV/slac/pull/3) Added env settings using environs lib, updated readme and docker compose files by @tropxy

### Fixed

- [#2](https://github.com/SwitchEV/slac/pull/2) added PYPI switch as extra-index by @tropxy

## [0.1.0] - 2021-11-20

- Initial release.
