import logging
import os
from dataclasses import dataclass
from typing import Optional

import environs

from pyslac.enums import Timers

logger = logging.getLogger(__name__)


@dataclass
class Config:
    slac_init_timeout: Optional[int] = None
    slac_atten_results_timeout: Optional[int] = None
    log_level: Optional[int] = None

    def load_envs(self, env_path: Optional[str] = None) -> None:
        """
        Tries to load the .env file containing all the project settings.
        If `env_path` is not specified, it will get the .env on the current
        working directory of the project
        Args:
            env_path (str): Absolute path to the location of the .env file
        """
        env = environs.Env(eager=False)
        if not env_path:
            env_path = os.getcwd() + "/.env"
        env.read_env(path=env_path)  # read .env file, if it exists

        # This timer is set in docker-compose.dev.yml, for merely debugging and dev
        # reasons
        self.slac_init_timeout = env.float(
            "SLAC_INIT_TIMEOUT", default=Timers.SLAC_INIT_TIMEOUT
        )

        self.slac_atten_results_timeout = env.int(
            "ATTEN_RESULTS_TIMEOUT",
            default=None
        )
        self.log_level = env.str("LOG_LEVEL", default="INFO")

        env.seal()  # raise all errors at once, if any
