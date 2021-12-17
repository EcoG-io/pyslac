import os
import logging
from dataclasses import dataclass
from typing import Optional

import environs

from slac.enums import Timers

logger = logging.getLogger(__name__)


@dataclass
class Config:
    iface: Optional[str] = None
    mqtt_host: Optional[str] = None
    mqtt_port: Optional[int] = None
    redis_host: Optional[str] = None
    redis_port: Optional[int] = None
    slac_init_timeout: Optional[int] = None
    log_level: Optional[int] = None

    def load_envs(self) -> None:
        env = environs.Env(eager=False)
        env_path = os.getcwd() + "/.env"
        env.read_env(path=env_path)  # read .env file, if it exists
        self.iface = env.str("NETWORK_INTERFACE", default="eth0")
        self.mqtt_host = env.str("MQTT_HOST")
        self.mqtt_port = env.int("MQTT_PORT")
        self.redis_host = env.str("REDIS_HOST")
        self.redis_port = env.int("REDIS_PORT")

        # This timer is set in docker-compose.dev.yml, for merely debugging and dev
        # reasons
        self.slac_init_timeout = env.float(
            "SLAC_INIT_TIMEOUT", default=Timers.SLAC_INIT_TIMEOUT
        )

        self.log_level = env.str("LOG_LEVEL", default="INFO")

        env.seal()  # raise all errors at once, if any
