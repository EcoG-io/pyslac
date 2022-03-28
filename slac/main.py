from slac.utils import is_distro_linux

if not is_distro_linux():
    raise EnvironmentError("Non-Linux systems are not supported")


import asyncio
import functools
import logging
from dataclasses import dataclass
from inspect import isawaitable
from typing import Any, List, Optional, Set

from asyncio_mqtt.client import Client
from mqtt_api.mqtt import Mqtt
from mqtt_api.routing import on
from mqtt_api.v1 import request, response
from mqtt_api.v1.enums import CpStates, MessageName, SlacStatus, Topics

from slac.enums import STATE_MATCHED, STATE_MATCHING, STATE_UNMATCHED
from slac.environment import Config
from slac.session import SlacEvseSession
from slac.utils import cancel_task, wait_till_finished

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("main")


@dataclass
class SlacStatusPayload:
    """
    Dataclass to hold the SlacStatus Payload info
    This class is here as it was missing from mqtt_api by the time this code
    was implemented.
    """
    evse_id: str
    status: SlacStatus


def get_session(f):
    """
    Decorator to get the session saved in the attribute running sessions
    of SlacHandler, based on the evse_id.
    """

    @functools.wraps(f)
    async def inner(self, *args, **kwargs):
        for session in self.running_sessions:
            if session.evse_id == kwargs["evse_id"]:
                response = f(self, session, *args, **kwargs)
                if isawaitable(response):
                    response = await response
                return response
        raise AttributeError(
            f"There is no running session with " f"evse_id {kwargs['evse_id']}"
        )

    return inner


class SlacHandler(Mqtt):
    def __init__(self, config: Config):
        super().__init__(
            mqtt_client=lambda: Client(config.mqtt_host, config.mqtt_port),
            topics=[Topics.CS_JOSEV],
            response_timeout=60,
        )
        self.config = config
        self.running_tasks: Set[asyncio.Task] = set()
        self.running_sessions: List["SlacEvseSession"] = []

    async def get_cs_parameters(self):
        """
        Task to request the cs_parameters of the station.

        The response shall contain a similar payload as follows:
        "id": "c2ff42ec-a6f6-4830-8916-440ac690bb9a",
        "name": "cs_parameters",
        "type": "response",
        "data": {
            "sw_version": "v1.0.1",
            "hw_version": "v2.0.0",
            "number_of_evses": 1,
            "parameters": [{
                    "evse_id": "DE*SWT*E123456789",
                    "supports_eim": False,
                    "network_interface": "eth0",
                    "connectors": [...],

        If no answer is provided in 60s, a timeout occurs and the slac application stops.
        If the Initialization of the Slac session based on the CS Parameters received
        fails, the system restarts awaiting for the parameters after 5 secs.

        Note:
            The evse_id provided must be unique and is assumed to be associated to
            one and one only network_interface. This is important, as the 'evse_id' is
            used in subsequent messages as an identifier of the running session.
        """
        while not self.running_sessions:
            cs_parameters: response.CsParametersPayload = await self.request(
                topic=Topics.JOSEV_CS, payload=request.CsParametersPayload()
            )

            if cs_parameters.number_of_evses < 1 or (
                    len(cs_parameters.parameters) != cs_parameters.number_of_evses
            ):
                raise AttributeError("Number of evses provided is invalid.")

            for evse_params in cs_parameters.parameters:
                # Initialize the Slac Session
                try:
                    slac_session = SlacEvseSession(
                        evse_params.evse_id, evse_params.network_interface, self.config
                    )
                    await slac_session.evse_set_key()
                except (OSError, asyncio.TimeoutError) as e:
                    logger.error(e(f"PLC chip initialization failed for "
                                   f"interface {evse_params.network_interface}: {e}. \n"
                                   f"Please check your CS parameters. The CS Parameters"
                                   f"request will be resent in 5 secs"))
                    self.running_sessions.clear()
                    await asyncio.sleep(5)
                    break
                self.running_sessions.append(slac_session)

    @get_session
    @on(MessageName.CP_STATUS)
    async def on_cp_status(
        self, slac_session: "SlacEvseSession", state: CpStates, **kwargs: Any
    ) -> None:
        """
        If it is the case a matching process is not ongoing
        and the CP has transited to state B, C or D, it spawns a new matching task,
        otherwise if transited to A, E or F and a matching task is running and
        the state is "Matched", it kills the task. This extra check for the
        state "Matched", is to avoid to kill the task during transitions to state
        E/F which can happen, e.g., if user does EIM after Plugin and before
        the first SLAC message is received.
        """
        # Some states contain the indication if the station can provide energy
        # or not (e.g. A1 - it cant, A2 it can); so we get only the first character
        # from the string, since is that what we are interested here.
        cp_state = state[0]
        logger.debug(f"CP State Received: {state}")
        if cp_state in ["A", "E", "F"] and slac_session.matching_process_task:
            if cp_state == "A" or slac_session.state == STATE_MATCHED:
                # We kill the task if a direct transition to state A is detected
                # or if E,F is detected and we are in state 'Matched'
                await cancel_task(slac_session.matching_process_task)
                logger.debug("Matching process task canceled")
                # leaving the logical network
                # In order to avoid writing too many times to the device,
                # we dont reset the NID and NMK between charging sessions for now
                # await slac_session.leave_logical_network()
                slac_session.matching_process_task = None
                logger.debug("Leaving Logical Network")
        elif cp_state in ["B", "C", "D"] and slac_session.matching_process_task is None:
            slac_session.matching_process_task = asyncio.create_task(
                self.matching_process(slac_session)
            )

    async def matching_process(
        self, slac_session: "SlacEvseSession", number_of_retries=3
    ) -> None:
        """
        Task that is spawned once a state change is detected from A, E or F to
        B, C or D. This task is responsible to run the right methods defined in
        session.py, which as a whole comprise the SLAC protocol.
        In case SLAC fails, it retries up to 3 times to get a match, and
        in case it fails again, it gives up and just with a transition to B, C or D,
        SLAC will restart.

        :param slac_session: Instance of SlacEVSESession
        :param number_of_retries: number of trials before SLAC Mathing is defined
        as a failure
        :return: None
        """
        while number_of_retries:
            number_of_retries -= 1
            await slac_session.evse_slac_parm()
            if slac_session.state == STATE_MATCHING:
                logger.debug("Matching ongoing...")
                await self.update(
                    topic=Topics.JOSEV_CS,
                    payload=SlacStatusPayload(
                        slac_session.evse_id, SlacStatus.MATCHING
                    ),
                )
                try:
                    await slac_session.atten_charac_routine()
                except Exception as e:
                    slac_session.state = STATE_UNMATCHED
                    logger.debug(f"Exception Occurred during Attenuation Charc Routine:"
                                 f"{e} \n"
                                 f"Number of retries left {number_of_retries}")
            if slac_session.state == STATE_MATCHED:
                logger.debug("PEV-EVSE MATCHED Successfully, Link Established")
                while True:
                    await asyncio.sleep(2.0)

                # The check of the link status wont be done using the message
                # LINK_STATUS, because it is not a proper way to check it since
                # it only provides a confirmation to the message
                # Instead, NW_INFO message is a better one

                # logger.debug("PEV-EVSE Link Lost")
                # leaving the logical network
                # In order to avoid writing too many times to the device,
                # we dont reset the NID and NMK between charging sessions for now
                # await slac_session.leave_logical_network()
                # slac_session.matching_process_task = None
                # break
            if slac_session.state == STATE_UNMATCHED:
                number_of_retries -= 1
                if number_of_retries > 0:
                    logger.warning("PEV-EVSE MATCHED Failed; Retrying..")
                else:
                    logger.error("PEV-EVSE MATCHED Failed: No more retries " "possible")
                    await self.update(
                        topic=Topics.JOSEV_CS,
                        payload=SlacStatusPayload(
                            slac_session.evse_id, SlacStatus.FAILED
                        ),
                    )
            else:
                logger.error(f"SLAC State not recognized {slac_session.state}")

        logger.debug("SLAC Protocol Concluded...")
        # TODO: May need to communicate to HLE that the link is lost (check section
        # 7.5 Loss of communication in -3). Send Unmatched
        # TODO: May need to communicate to CS that the link is gone, so that
        # Basic Charging can be tried
        await slac_session.leave_logical_network()


async def main(env_path: Optional[str] = None):
    # get configuration
    config = Config()
    config.load_envs(env_path)

    slac_handler = SlacHandler(config)
    # Spawn the cs_parameters and the mqtt incoming task
    tasks = [slac_handler.start(), slac_handler.get_cs_parameters()]
    await wait_till_finished(tasks)


def run():
    asyncio.run(main())


if __name__ == "__main__":
    run()
