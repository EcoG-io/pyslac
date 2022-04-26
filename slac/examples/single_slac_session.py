from slac.utils import is_distro_linux

if not is_distro_linux():
    raise EnvironmentError("Non-Linux systems are not supported")

import asyncio
import json
import logging
from typing import List, Optional

from slac.environment import Config
from slac.session import SlacEvseSession, SlacSessionController
from slac.utils import wait_till_finished

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__file__)


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


async def main(env_path: Optional[str] = None):
    # get configuration
    slac_config = Config()
    slac_config.load_envs(env_path)

    json_file = open("cs_configuration.json")
    cs_config = json.load(json_file)
    json_file.close()
    slac_handler = SlacHandler(slac_config)
    tasks = [slac_handler.start(cs_config)]
    await wait_till_finished(tasks)


def run():
    asyncio.run(main())


if __name__ == "__main__":
    run()
