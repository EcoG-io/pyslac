from pyslac.utils import is_distro_linux

if not is_distro_linux():
    raise EnvironmentError("Non-Linux systems are not supported")

import asyncio
import json
import logging
import os
from typing import List, Optional

from pyslac.environment import Config
from pyslac.session import SlacEvseSession, SlacSessionController
from pyslac.utils import wait_for_tasks

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__file__)


class SlacHandler(SlacSessionController):
    def __init__(self, slac_config: Config):
        SlacSessionController.__init__(self)
        self.slac_config = slac_config
        self.running_sessions: List["SlacEvseSession"] = []

    async def notify_matching_ongoing(self, evse_id: str):
        """overrides the notify matching ongoing method defined in
        SlacSessionController"""
        logger.info(f"Matching is ongoing for {evse_id}")

    async def enable_hlc_charging(self, evse_id: str):
        """
        overrides the enable_hlc_charging method defined in SlacSessionController
        """
        logger.info(f"Enable PWM and set 5% duty cycle for evse {evse_id}")

    async def start(self, cs_config: dict):
        if cs_config["number_of_evses"] < 1 or (
            len(cs_config["parameters"]) != cs_config["number_of_evses"]
        ):
            raise AttributeError("Number of evses provided is invalid.")

        evse_params: dict = cs_config["parameters"][0]
        evse_id: str = evse_params["evse_id"]
        network_interface: str = evse_params["network_interface"]
        try:
            slac_session = SlacEvseSession(evse_id, network_interface, self.slac_config)
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

        await self.enable_hlc_and_trigger_slac(self.running_sessions[0])

    async def enable_hlc_and_trigger_slac(self, session):
        """
        Dummy method to fake the enabling of the HLC by setting PWM to 5%
        and triggers the Matching by handling a CP state change to "B"
        """
        await self.enable_hlc_charging(session.evse_id)
        await self.process_cp_state(session, "B")
        await asyncio.sleep(2)
        await self.process_cp_state(session, "C")
        await asyncio.sleep(20)
        await self.process_cp_state(session, "A")


async def main(env_path: Optional[str] = None):
    # get configuration
    slac_config = Config()
    slac_config.load_envs(env_path)
    root_dir = os.path.dirname(os.path.abspath(__file__))
    json_file = open(os.path.join(root_dir, "cs_configuration.json"))
    cs_config = json.load(json_file)
    json_file.close()
    slac_handler = SlacHandler(slac_config)
    tasks = [slac_handler.start(cs_config)]
    await wait_for_tasks(tasks)


def run():
    asyncio.run(main())


if __name__ == "__main__":
    run()
