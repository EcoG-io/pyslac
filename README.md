# SLAC

Python Implementation of the SLAC Protocol as specified by ISO15118-3 [^1]

## How to fire it up :fire:

Slac main.py file lives under the `slac` directory. The project depends on an
installation of slac as a module in your current environment. Dependencies
management are handled by `Poetry`.

> Dependencies:
>
> - Poetry [^2]
> - Python >= 3.9

There are two recommended ways of running the project:

1. Building and running the docker file:

   ```bash
   $ make build
   $ make dev
   ```

2. Installing the module using `poetry` and running the main script, which
   steps are compiled with the help of the Makefile:

   ```bash
   $ make install-local
   $ make run-local
   ```

In order to start the SLAC session, it is required to provide some information
like the network intarface(s) where the Power Line Communication is associated to.


The project includes a few configuration variables, whose default
values can be modified by setting them as environmental variables.
The following table provides a few of the available variables:

| ENV               | Default Value         | Description                                                                    |
| ----------------- | --------------------- | ------------------------------------------------------------------------------ |
| SLAC_INIT_TIMEOUT | `50`                  | Timeout[s] for the reception of the first slac message after state B detection | |
| LOG_LEVEL         | `INFO`                | Level of the Python log service                                                |


The project includes a few environmental files, in the root directory, for 
different purposes:

* `.env.dev.docker` - ENV file with development settings, tailored to be used with docker
* `.env.dev.local` - ENV file with development settings, tailored to be used with 
the local host

If the user runs the project locally, e.g. using `$ make install-local && make run-local`,
it is required to create a `.env` file, containing the required settings.

This means, if development settings are desired, one can simply copy the contents
of `.env.dev.local` to `.env`.

If Docker is used, the command `make run` will try to get the `.env` file;
The command `make dev` will fetch the contents of `.env.dev.docker` - thus,
in this case, the user does not need to create a `.env` file, as Docker will
automatically fetch the `.env.dev.docker` one.

The key-value pairs defined in the `.env` file directly affect the settings
present in `slac/environment.py`. In this script, the user will find all the settings that can be configured.

Any of those variables can also be set by exporting their value in the env:

`$ export NETWORK_INTERFACE=eth1`



## Known Issues and Limitation

1`make run-local` may not work in your system

   SLAC requires the use of Level 2 frames, as so, the app requires low level access to
   the socket interface. Such level of access is only attained with root priviliges, so
   if the user group that your system is using does not have root priviliges, the app will
   fail to run.

   In order to run the app with root priviliges, try the following command, instead:
   `$ make run-local-sudo`

## Integration Test with an EV SLAC Simulator

The EVSE SLAC code can be tested against the EV counterpart. For convenience,
a simple EV SLAC version was programmed using scapy. The code is located under
the folder `examples/ev_slac_scapy.py` and contains all the necessary SLAC
messages as well the right and expected sequence of messages that must be sent
to the EVSE to complete SLAC. This code doesnt perform any check on the payloads
received, thus is not a complete bullet-proof test system.

To start the test, you may need root privileges and to start in the following
order:

```bash
$ sudo $(shell which python) slac/main.py
$ sudo $(shell which python) slac/examples/ev_slac_scapy.py
```

This integration test was tested under:

- Linux - Ubuntu and Debian distros

[^1]: https://www.iso.org/standard/59675.html
[^2]: https://python-poetry.org/docs/#installation
