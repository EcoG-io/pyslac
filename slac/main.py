from slac.utils import is_distro_linux

if not is_distro_linux():
    raise EnvironmentError("Non-Linux systems are not supported")


import asyncio
import logging
from typing import List, Optional, Set

from slac.environment import Config
from slac.session import SlacEvseSession, SlacSessionController
from slac.utils import wait_till_finished

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("main")

EVSE_ID = "DE*SW*A234546"
NETWORK_INTERFACE = "eth0"


class SlacHandler(SlacSessionController):
    def __init__(self, config: Config):
        SlacSessionController.__init__(self)
        self.config = config
        self.running_tasks: Set[asyncio.Task] = set()
        self.running_sessions: List["SlacEvseSession"] = []

    async def start(self, evse_id: str, network_interface: str):
        while not self.running_sessions:
            try:
                slac_session = SlacEvseSession(evse_id, network_interface, self.config)
                await slac_session.evse_set_key()
                self.running_sessions.append(slac_session)
            except (OSError, TimeoutError, ValueError) as e:
                logger.error(
                    f"PLC chip initialization failed for "
                    f"EVSE {evse_id}, interface "
                    f"{network_interface}: {e}. \n"
                    f"Please check your settings."
                )
                self.running_sessions.clear()
                await asyncio.sleep(5)
                continue
            await self.process_cp_status(slac_session, "B")
            await asyncio.sleep(2)
            await self.process_cp_status(slac_session, "C")
            await asyncio.sleep(20)
            await self.process_cp_status(slac_session, "A")


async def main(env_path: Optional[str] = None):
    # get configuration
    config = Config()
    config.load_envs(env_path)

    slac_handler = SlacHandler(config)
    # Spawn the cs_parameters and the mqtt incoming task
    tasks = [slac_handler.start(EVSE_ID, NETWORK_INTERFACE)]
    await wait_till_finished(tasks)


def run():
    asyncio.run(main())


if __name__ == "__main__":
    run()
