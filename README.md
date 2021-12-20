# SLAC

Python Implementation of the SLAC Protocol as specified by ISO15118-3 [^1]

## How to fire it up :fire:

Slac main.py file lives under the `slac`directory. The project depends on an
installation of slac as a module in your current environment and dependencies
management is handled by `Poetry`.

> Dependencies:
>
> - Poetry [^2]
> - Python >= 3.7

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

For a successful dependencies installation, you will need to provide the
credentials to the Switch PyPi private server:

   ```shell
   $ export PYPI_USER=****
   $ export PYPI_PASS=****
   ```
Contact André <andre@switch-ev.com> if you have questions about it.

The last required step to effectively start the SLAC mechanism, is to force the
detection of state `B`of the Control Pilot circuit. This project relies on
a request/response API based on a pub/sub philosophy adopted by MQTT.
Thus, in order to force the algorithm to listen for SLAC frames, we need a
MQTT broker and a client that sends a message notifying the Control Pilot state;
This is demonstrated in the following snippet, where it is assumed we are using
a public available broker from HiveMQ with no authorization settings.

```python
async with Client("broker.hivemq.com") as client:
    message = {"id": 2, "name": "cp_status", "type": "update",
               "data": {"evse_id": "DE-SWT-E123456789", "state": "B1"}}
    await client.publish("slac/cs", payload=json.dumps(message), qos=2, retain=False)
```

For more information about the MQTT API used by Switch check the following link:
https://app.gitbook.com/@switch-ev/s/josev-api/

Finally, the project includes a few configuration variables, whose default
values can be modified by setting them as environmental variables.
The following table provides a few of the available variables:

| ENV               | Default Value         | Description                                                                    |
| ----------------- | --------------------- | ------------------------------------------------------------------------------ |
| NETWORK_INTERFACE | `"eth0"`              | HomePlug Network Interface                                                     |
| SLAC_INIT_TIMEOUT | `50`                  | Timeout[s] for the reception of the first slac message after state B detection |
| MQTT_HOST         | No Default            | MQTT Broker URL                                                                |
| MQTT_PORT         | No Default            | MQTT Broker Port                                                               |
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

1. `make install-local`or `make poetry-update` may fail, depending on your system.
   Poetry relies on the `Keyring` of your system and, unfortunately, this can create
   problems. The common outcome is that Poetry won't authenticate against the
   Switch private PyPi server:
   ```shell
   RepositoryError
       403 Client Error: Forbidden for url: https://pypi.switch-ev.com/simple/flake8/
   ```
   There are two possible solutions:
   1. Explicitly inject the credentials into pyproject.toml
      For that you can use the following command:
      `$ make set-credentials`
   2. Disable your Keyring for Python, following the steps on this page:
      https://blog.frank-mich.com/python-poetry-1-0-0-private-repo-issue-fix/

   If you follow one of the above steps, the installation shall run smoothly.

2. `make run-local` may not work in your system

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
$ sudo python slac/main.py
$ sudo python slac/examples/ev_slac_scapy.py
```

This integration test was tested under:

- Linux - Ubuntu and Debian distros

[^1]: https://www.iso.org/standard/59675.html
[^2]: https://python-poetry.org/docs/#installation
