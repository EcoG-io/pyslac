import logging

import environs

from slac.enums import Timers

logger = logging.getLogger(__name__)


env = environs.Env(eager=False)
env.read_env()  # read .env file, if it exists

NETWORK_INTERFACE = env.str("NETWORK_INTERFACE", default="eth0")
MQTT_HOST = env("MQTT_HOST")
MQTT_PORT = env.int("MQTT_PORT")
REDIS_HOST = env.str("REDIS_HOST")
REDIS_PORT = env.int("REDIS_PORT")

# This timer is set in docker-compose.dev.yml, for merely debugging and dev
# reasons
SLAC_INIT_TIMEOUT = env.float("SLAC_INIT_TIMEOUT", default=Timers.SLAC_INIT_TIMEOUT)

LOG_LEVEL = env.str("LOG_LEVEL", default="INFO")


env.seal()  # raise all errors at once, if any
