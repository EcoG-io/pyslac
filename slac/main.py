from typing import Optional
from slac.utils import is_distro_linux

if not is_distro_linux():
    raise EnvironmentError("Non-Linux systems are not supported")

import asyncio
import json
import logging
from dataclasses import asdict

from asyncio_mqtt import Client
from asyncio_mqtt.client import ProtocolVersion
from mqtt_api import validator
from mqtt_api.enums import (
    ActionType,
    JOSEVAPIMessage,
    MessageName,
    MessageStatus,
    SlacStatus,
    Topics,
)

from slac.enums import EVSE_ID, STATE_MATCHED, STATE_MATCHING, STATE_UNMATCHED
from slac.environment import Config
from slac.session import SlacEvseSession
from slac.utils import cancel_task, mqtt_send, wait_till_finished

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("main")


async def control_pilot_monitoring(slac_session: "SlacEvseSession"):
    """
    Task to constantly monitor the Control Pilot state
    """
    async with Client(
        hostname=slac_session.config.mqtt_host,
        port=slac_session.config.mqtt_port,
        protocol=ProtocolVersion.V31,
    ) as client:
        async with client.filtered_messages(Topics.SLAC_CS) as messages:
            # subscribe is done afterwards so that we just start receiving
            # messages from this point on
            await client.subscribe(Topics.SLAC_CS)
            async for message_encoded in messages:
                message = json.loads(message_encoded.payload)
                if message.get("name") not in [
                    MessageName.SLAC_STATUS,
                    MessageName.CP_STATUS,
                ]:
                    logger.warning(f"Unexpected Message {message.get('name')}")
                    continue
                try:
                    validator.validate_message(message)
                    data_field = {"status": MessageStatus.ACCEPTED}
                except validator.MqttApiValidationError as exp:
                    logger.exception(f"Schema Validation Failed {exp}")
                    data_field = {"status": MessageStatus.REJECTED}

                if message.get("type") == ActionType.RESPONSE:
                    # if the message is of the type Response, then just return
                    # nevertheless, validation is done first just to check
                    # if there were issues with it
                    logger.debug(
                        f"Status Response for {message['name']} "
                        f"is: {message['data']}"
                    )
                    continue

                answer = JOSEVAPIMessage(
                    id=message["id"],
                    name=message["name"],
                    type=ActionType.RESPONSE,
                    data=data_field,
                )
                await mqtt_send(asdict(answer), Topics.SLAC_JOSEV, slac_session.config)
                if data_field["status"] == MessageStatus.ACCEPTED:
                    await process_mqtt_message(slac_session, message)


async def process_mqtt_message(slac_session: "SlacEvseSession", message: dict):
    """
    Handler to process incoming MQTT messages
    If the message is not of the kind "cp_status", it ignores the message
    otherwise processes it. If it is the case a matching process is not ongoing
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
    cp_state = message["data"]["state"][0]
    logger.debug(f"CP State Received: {message['data']['state']}")
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
            matching_process(slac_session)
        )


async def matching_process(slac_session: "SlacEvseSession", number_of_retries=3):
    """
    Task that is spawned once a state change is detected from A. E or F to
    B, C or D. This task is responsible to run the right methods defined in
    session.py which as whole comprise the SLAC protocol.
    In case of matching runs a while loop which check for the state of the
    Data Link. In case SLAC fails, it retries up to 3 times to get a match, and
    in case it fails, it gives up and just with a transition to B, C or D, will
    restart SLAC.

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
            # TODO: populate this field with locally stored data
            data_field = {"evse_id": EVSE_ID, "status": SlacStatus.MATCHING}
            slac_session.mqtt_msg_counter += 1
            message = JOSEVAPIMessage(
                id=slac_session.mqtt_msg_counter,
                name=MessageName.SLAC_STATUS,
                type=ActionType.UPDATE,
                data=data_field,
            )
            await mqtt_send(asdict(message), Topics.SLAC_JOSEV, slac_session.config)
            await slac_session.atten_charac_routine()
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
                data_field = {"evse_id": EVSE_ID, "status": SlacStatus.FAILED}
                slac_session.mqtt_msg_counter += 1
                message = JOSEVAPIMessage(
                    id=slac_session.mqtt_msg_counter,
                    name=MessageName.SLAC_STATUS,
                    type=ActionType.UPDATE,
                    data=data_field,
                )
                await mqtt_send(asdict(message), Topics.SLAC_JOSEV, slac_session.config)
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
    # Initialize the Slac Session
    slac_session = SlacEvseSession(config)
    await slac_session.evse_set_key()
    # Spawn the control pilot monitor task
    task = [control_pilot_monitoring(slac_session)]
    await wait_till_finished(task)


def run():
    asyncio.run(main())


if __name__ == "__main__":
    run()
