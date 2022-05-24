# SLAC

Python Implementation of the SLAC Protocol as specified by ISO15118-3 [^1]

## How to test it and fire it up :fire:

The project depends on an installation of slac as a module in the user environment.
Dependencies management is handled by `Poetry`.

> Dependencies:
>
> - Poetry [^2]
> - Python >= 3.9

The project presents examples of how to spin up the SLAC session, for one or multiple
EVSEs which are associated with a specific network interface.
The `SlacSession` class defined in `slac/session.py` expects
the `evse id` and the `network interface` as arguments, this because SLAC requires
to bind to a network interface. To ease the passing of these arguments, a json file
named `cs_configuration.json` includes a configuration example containing the EVSE id
and the network interface for two EVSEs:
```json
{
  "number_of_evses": 2,
  "parameters": [
	{"evse_id": "DE*SWT*E123456789",
	  "network_interface": "eth0"
	},
	{"evse_id": "DE*SWT*E5131456589",
	  "network_interface": "eth1"
	}
  ]
}
```

There are two  ways of running the examples:

1. Building and running the docker file will run the `single_slac_session.py`:

   ```bash
   $ make build
   $ make dev
   ```

2. Installing the module using `poetry` and running one of the examples, which
   steps are compiled with the help of the Makefile:

   ```bash
   $ make install-local
   $ make run-local-single
   ```

Both the single and multiple session examples have the same structure:
```python
class SlacHandler(SlacSessionController):
    def __init__(self, slac_config: Config):
        SlacSessionController.__init__(self)
        self.slac_config = slac_config
        self.running_sessions: List["SlacEvseSession"] = []

    async def start(self, cs_config: dict):
        while not self.running_sessions:
            if cs_config["number_of_evses"] < 1 or (
                len(cs_config["parameters"]) != cs_config["number_of_evses"]
            ):
                raise AttributeError("Number of evses provided is invalid.")

            evse_params: dict = cs_config["parameters"][0]
            evse_id: str = evse_params["evse_id"]
            network_interface: str = evse_params["network_interface"]
            try:
                slac_session = SlacEvseSession(
                    evse_id, network_interface, self.slac_config
                )
                await slac_session.evse_set_key()
                self.running_sessions.append(slac_session)
            except (OSError, TimeoutError, ValueError) as e:
                logger.error(
                    f"PLC chip initialization failed for "
                    f"EVSE {evse_id}, interface "
                    f"{network_interface}: {e}. \n"
                    f"Please check your settings."
                )
                return
        await self.process_cp_state(self.running_sessions[0], "B")
        await asyncio.sleep(2)
        await self.process_cp_state(self.running_sessions[0], "C")
        await asyncio.sleep(20)
        await self.process_cp_state(self.running_sessions[0], "A")
```
Both start by attempting to create a `SlacEvseSession` for each evse, which network
interface is defined in the `cs_config` dictionary. If, for example, the network
interface defined does not exist, the system will raise an error and exit.

Both define a class named `SlacHandler`, which inherits from `SlacSessionController`.
The `SlacSessionController` has two main methods `process_cp_state` and `start_matching`.
The `process_cp_state` is a handler for the state change of the Control Pilot circuit
and based on a state transition from "A, E or F" to "B, C or D", the `start_matching`
is spawned as an asyncio task.
Is that task that handles the SLAC matching process and that ultimately succeeds or
fails the attempt.

That task includes calls to two stub methods `notify_matching_ongoing` and
`notify_matching_failed`, which can be used by the end user to notify other services
of the current SLAC matching state ("ongoing" or "failed"). This can be useful
for the use case defined in ISO 15118-3, section 7, where different strategies need
be carried on, depending on if SLAC matching has started after or before EIM
authentication was completed.

The example is a very raw way to trigger the matching process and does not represent
a real production scenario. In a more realistic scenario, the user may use any way to
communicate the Control Pilot state to SLAC, e.g., using MQTT or RabbitMQ as message
brokers.

In that case, the user would have some external service monitoring the Control Pilot
state, which would send the state to the SLAC application. The Slac Handler would then
be waiting, listening for the Control Pilot state notification and on reception of it,
would call the `process_cp_state`, which in its turn would spawn a matching process task.


## Environmental Settings

The project also includes a few general configuration variables, whose default values
can be modified by setting them as environmental variables.

The following table provides a few of the available variables:

| ENV               | Default Value         | Description                                                                    |
| ----------------- | --------------------- | ------------------------------------------------------------------------------ |
| SLAC_INIT_TIMEOUT | `50`                  | Timeout[s] for the reception of the first slac message after state B detection | |
| LOG_LEVEL         | `INFO`                | Level of the Python log service                                                |


These env variables, can be modified using `.env` files, which this project includes,
in the root directory, for different purposes:

* `.env.dev.docker` - ENV file with development settings, tailored to be used with docker
* `.env.dev.local` - ENV file with development settings, tailored to be used with 
the local host

If the user runs the project locally, e.g. using `$ make install-local && make run-local-single`,
the system will look for  a `.env` file, containing the required settings.

This means, if development settings are desired, one can simply copy the contents
of `.env.dev.local` to `.env`.

If Docker is used, the command `make run` will try to get the `.env` file;
The command `make dev` will fetch the contents of `.env.dev.docker` - thus,
in this case, the user does not need to create a `.env` file, as Docker will
automatically fetch the `.env.dev.docker` one.

The key-value pairs defined in the `.env` file directly affect the settings present in
`slac/environment.py`.

Any of those variables can also be set by exporting their value in the env:

`$ export NETWORK_INTERFACE=eth1`



## Known Issues and Limitation

1. `make run-local-single` may not work in your system

   SLAC requires the use of Level 2 frames, as so, the app requires low level access to
   the socket interface. Such level of access is only attained with root privileges, so
   if the user group that your system is using does not have root privileges, the app will
   fail to run.

   In order to run the app with root privileges, try the following command, instead:
   `$ make run-local-sudo-single`

## Integration Test with an EV SLAC Simulator

The EVSE SLAC code can be tested against the EV counterpart. For convenience,
a simple EV SLAC version was programmed using scapy. The code is located under
the folder `examples/ev_slac_scapy.py` and contains all the necessary SLAC
messages as well the right and expected sequence of messages that must be sent
to the EVSE to complete SLAC. This code doesn't perform any check on the payloads
received, thus is not a complete bullet-proof test system.

To start the test, you may need root privileges and to start in the following
order:

```bash
$ sudo $(shell which python) pyslac/examples/single_slac_session.py
$ sudo $(shell which python) pyslac/examples/ev_slac_scapy.py
```

This integration test was tested under:

- Linux - Ubuntu and Debian distros

[^1]: https://www.iso.org/standard/59675.html
[^2]: https://python-poetry.org/docs/#installation
