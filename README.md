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

   If you follow this path, then you will need to provide the PYPI credentials
   and export them as ENVs:

   ```shell
   $ export PYPI_USER=****
   $ export PYPI_PASS=****
   ```

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

Finally, the project includes a few configuration variables whose default
values can be modified by setting them as an environmental variable:

| ENV               | Default Value         | Description                                                                    |
| ----------------- | --------------------- | ------------------------------------------------------------------------------ |
| NETWORK_INTERFACE | `"eth0"`              | HomePlug Network Interface                                                     |
| SLAC_INIT_TIMEOUT | `50`                  | Timeout[s] for the reception of the first slac message after state B detection |
| MQTT_URL          | `"broker.hivemq.com"` | MQTT Broker URL                                                                |
| MQTT_USER         | `None`                | Username for Client Authorization                                              |
| MQTT_PASS         | `None`                | Password for Client Authorization                                              |

Any of those variables can be set by exporting their value in the env:

`$ export NETWORK_INTERFACE=eth1`

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
