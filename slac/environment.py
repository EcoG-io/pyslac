import json
import os
from contextlib import suppress

from slac.enums import Timers


def load_from_env(variable, default=None):
    """Read values from the environment and try to convert values from json"""
    value = os.environ.get(variable, default)
    if value is not None:
        with suppress(json.decoder.JSONDecodeError, TypeError):
            value = json.loads(value)
    return value


# This timer is set in docker-compose.dev.yml, for merely debugging and dev
# reasons
SLAC_INIT_TIMEOUT = load_from_env("SLAC_INIT_TIMEOUT", default=Timers.SLAC_INIT_TIMEOUT)
NETWORK_INTERFACE = load_from_env("NETWORK_INTERFACE", default="eth0")
MQTT_URL = load_from_env("MQTT_URL", default="broker.hivemq.com")
MQTT_USER = load_from_env("MQTT_USER")
MQTT_PASS = load_from_env("MQTT_PASS")
