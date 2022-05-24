# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.8.1] - 2022-05-24

### Changed
- switched the package upload to public pypi server by @tropxy in https://github.com/SwitchEV/slac/pull/24
- refactored the package name to pyslac by @tropxy in https://github.com/SwitchEV/pyslac/pull/26

## [0.7.1] - 2022-04-28

### Added

- Added a way to log the exceptions that otherwise would go unnoticed by @tropxy in https://github.com/SwitchEV/slac/pull/21
- downgraded the python min version supported to 3.7 for more broad compatibility

## [0.7.0] - 2022-04-26

### Removed

- removed references of the switch mqtt API  by @tropxy in https://github.com/SwitchEV/slac/pull/18

### Added

- added enable_hlc_charging as a method of SlacSessionController  by @tropxy in https://github.com/SwitchEV/slac/pull/19


## [0.6.0] - 2022-04-12

### Changed

- Message process retry after unexpected message arrival by @tropxy in https://github.com/SwitchEV/slac/pull/13

## [0.5.0] - 2022-03-24

### Changed

- Network interface extraction from cs parameters; Update of the code with mqtt version 0.18.1 by @tropxy in https://github.com/SwitchEV/slac/pull/10

### Fixed

- Set credentials by @tropxy in https://github.com/SwitchEV/slac/pull/8
- Version bump by @tropxy in https://github.com/SwitchEV/slac/pull/11

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
