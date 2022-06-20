from unittest.mock import AsyncMock, Mock, patch

import pytest

from pyslac.enums import (
    BROADCAST_ADDR,
    CM_ATTEN_CHAR,
    CM_ATTEN_PROFILE,
    CM_SET_CCO_CAPAB,
    CM_SET_KEY,
    CM_SET_KEY_MY_NONCE,
    CM_SET_KEY_PID,
    CM_SET_KEY_PMN,
    CM_SET_KEY_PRN,
    CM_SET_KEY_YOUR_NONCE,
    CM_SLAC_MATCH,
    CM_SLAC_PARM,
    CM_START_ATTEN_CHAR,
    EVSE_PLC_MAC,
    MMTYPE_CNF,
    MMTYPE_IND,
    MMTYPE_REQ,
    MMTYPE_RSP,
    QUALCOMM_NID,
    QUALCOMM_NMK,
    SLAC_APPLICATION_TYPE,
    SLAC_ATTEN_TIMEOUT,
    SLAC_GROUPS,
    SLAC_MSOUNDS,
    SLAC_SECURITY_TYPE,
    STATE_MATCHED,
    STATE_MATCHING,
    STATE_UNMATCHED,
)
from pyslac.layer_2_headers import EthernetHeader, HomePlugHeader
from pyslac.messages import AttenProfile  # MnbcSound,
from pyslac.messages import (
    AtennChar,
    AtennCharRsp,
    MatchCnf,
    MatchReq,
    SetKeyCnf,
    SetKeyReq,
    SlacParmCnf,
    SlacParmReq,
    StartAtennChar,
)
from pyslac.utils import half_round as hw

PEV_MAC = b"\xBB" * 6
RUN_ID = b"\xFA" * 8
CONFIG_ATTEN_TIMEOUT = 1200


@pytest.mark.asyncio
async def test_set_key(evse_slac_session, dummy_config, evse_mac):
    """
    Tests the SetKey Req/Cnf sequence which just happens between the
    host and the QCA PLC Chip
    """
    # SetKey Request payload
    ethernet_header = EthernetHeader(dst_mac=EVSE_PLC_MAC, src_mac=evse_mac)
    homeplug_header = HomePlugHeader(CM_SET_KEY | MMTYPE_REQ)

    # Due to the temp change to use a static NID and NMK, we need to change
    # this message to pass the test
    # key_req_payload = SetKeyReq(nid=NID, new_key=NMK)
    key_req_payload = SetKeyReq(nid=QUALCOMM_NID, new_key=QUALCOMM_NMK)

    key_req_frame = (
        ethernet_header.pack_big()
        + homeplug_header.pack_big()
        + key_req_payload.pack_big()
    )

    # SetKey Confirmation payload
    homeplug_header = HomePlugHeader(CM_SET_KEY | MMTYPE_CNF)
    key_cnf_payload = SetKeyCnf(
        result=0x00,
        my_nonce=CM_SET_KEY_MY_NONCE,
        your_nonce=CM_SET_KEY_YOUR_NONCE,
        pid=CM_SET_KEY_PID,
        prn=CM_SET_KEY_PRN,
        pmn=CM_SET_KEY_PMN,
        cco_capab=CM_SET_CCO_CAPAB,
    )
    key_cnf_frame = (
        ethernet_header.pack_big()
        + homeplug_header.pack_big()
        + key_cnf_payload.pack_big()
    )
    # This first patch is to change the original SETTLE_TIME of 10 sec
    # so that during tests we dont wait so long
    evse_slac_session.send_frame = AsyncMock()
    with patch("pyslac.session.SLAC_SETTLE_TIME", 0.5):
        with patch("pyslac.session.readeth", new=AsyncMock(return_value=key_cnf_frame)):
            with patch("pyslac.session.urandom", new=Mock(return_value=QUALCOMM_NMK)):
                data_rcvd = await evse_slac_session.evse_set_key()

                assert data_rcvd == key_cnf_frame

                # check that what was sent through the send_rcv command was the
                # SetKey Request
                evse_slac_session.send_frame.assert_called_with(key_req_frame)


@pytest.mark.asyncio
async def test_slac_parm(evse_slac_session, evse_mac):
    """
    Tests the Slac Parm sequence
    """

    # Slac Parm Request payload
    ethernet_header = EthernetHeader(dst_mac=evse_mac, src_mac=PEV_MAC)
    homeplug_header = HomePlugHeader(CM_SLAC_PARM | MMTYPE_REQ)
    slac_parm_req = SlacParmReq(RUN_ID)

    slac_parm_req_frame = (
        ethernet_header.pack_big()
        + homeplug_header.pack_big()
        + slac_parm_req.pack_big()
    )

    # SlacParmCnf Confirmation payload
    ether_header = EthernetHeader(dst_mac=PEV_MAC, src_mac=evse_mac)
    homeplug_header = HomePlugHeader(CM_SLAC_PARM | MMTYPE_CNF)
    slac_parm_cnf = SlacParmCnf(forwarding_sta=ethernet_header.src_mac, run_id=RUN_ID)
    slac_parm_cnf_frame = (
        ether_header.pack_big() + homeplug_header.pack_big() + slac_parm_cnf.pack_big()
    )
    with patch(
        "pyslac.session.readeth", new=AsyncMock(return_value=slac_parm_req_frame)
    ):
        evse_slac_session.send_frame = AsyncMock()
        await evse_slac_session.evse_slac_parm()

        assert evse_slac_session.application_type == slac_parm_req.application_type
        assert evse_slac_session.security_type == slac_parm_req.security_type
        assert evse_slac_session.run_id == slac_parm_req.run_id
        evse_slac_session.send_frame.assert_called_with(slac_parm_cnf_frame)

        assert evse_slac_session.state == STATE_MATCHING


#         TODO: TEst for FAILURE!!!


@pytest.mark.asyncio
async def test_cm_start_atten_charac(evse_slac_session):
    """
    Tests Slac Start Attenuation Characterisation sequence
    """

    # Slac Attten Charc IND payload
    ethernet_header = EthernetHeader(dst_mac=BROADCAST_ADDR, src_mac=PEV_MAC)
    homeplug_header = HomePlugHeader(CM_START_ATTEN_CHAR | MMTYPE_IND)
    start_atten_car = StartAtennChar(
        num_sounds=SLAC_MSOUNDS,
        time_out=SLAC_ATTEN_TIMEOUT,
        forwarding_sta=PEV_MAC,
        run_id=RUN_ID,
    )

    start_atten_car_frame = (
        ethernet_header.pack_big()
        + homeplug_header.pack_big()
        + start_atten_car.pack_big()
    )
    with patch(
        "pyslac.session.readeth", new=AsyncMock(return_value=start_atten_car_frame)
    ):
        # Fake that we already received these parameters before, during
        # SLAC Param message sequence
        evse_slac_session.application_type = SLAC_APPLICATION_TYPE
        evse_slac_session.security_type = SLAC_SECURITY_TYPE
        evse_slac_session.run_id = RUN_ID

        await evse_slac_session.cm_start_atten_charac()

        assert evse_slac_session.num_expected_sounds == SLAC_MSOUNDS
        assert evse_slac_session.time_out_ms == SLAC_ATTEN_TIMEOUT * 100
        assert evse_slac_session.forwarding_sta == PEV_MAC

        # Test to assert that if the config is used, the session timeout is
        # set by the config and not by the StartAttenChar message
        evse_slac_session.config.slac_atten_results_timeout = CONFIG_ATTEN_TIMEOUT
        await evse_slac_session.cm_start_atten_charac()
        assert evse_slac_session.time_out_ms == CONFIG_ATTEN_TIMEOUT


@pytest.mark.asyncio
async def test_cm_mnbc_sound(evse_slac_session, evse_mac):
    """
    Tests MNBC Sound
    """
    # Slac Attten Profile payload
    ethernet_header = EthernetHeader(dst_mac=evse_mac, src_mac=EVSE_PLC_MAC)
    homeplug_header = HomePlugHeader(CM_ATTEN_PROFILE | MMTYPE_IND)
    num_expected_sounds = 3
    num_groups = 3
    aag_group = [20, 30, 10]
    atten_profile_ind = AttenProfile(
        pev_mac=PEV_MAC, aag=aag_group, num_groups=num_groups
    )

    atten_profile_ind_frame = (
        ethernet_header.pack_big()
        + homeplug_header.pack_big()
        + atten_profile_ind.pack_big()
    )

    with patch(
        "pyslac.session.readeth", new=AsyncMock(return_value=atten_profile_ind_frame)
    ):
        # mocking of data that is set in previous steps
        # The timeout is set here, because originally it would be only
        # SLAC_ATTEN_TIMEOUT, but we need it converted to ms, mainly
        # because the ci job takes more time to finish and it would fail
        # the test
        evse_slac_session.time_out_ms = SLAC_ATTEN_TIMEOUT * 100
        evse_slac_session.pev_mac = PEV_MAC
        evse_slac_session.num_expected_sounds = num_expected_sounds

        await evse_slac_session.cm_sounds_loop()
        aag_result = [0] * SLAC_GROUPS
        running_aag = [0] * SLAC_GROUPS
        # Simulation of the summation of all sounds received per group
        for sounds_received in range(num_expected_sounds):
            for group in range(num_groups):
                running_aag[group] += aag_group[group]
        for group in range(SLAC_GROUPS):
            aag_result[group] = hw(
                running_aag[group] / evse_slac_session.num_total_sounds
            )
        assert evse_slac_session.aag == aag_result


@pytest.mark.asyncio
async def test_cm_atten_charac(evse_slac_session, evse_mac):
    """
    Tests Slac Attenuation Characterisation sequence
    """
    num_total_sounds = 3
    num_groups = 3
    aag = [20, 30, 10]

    # Slac Atten Charc IND payload
    ethernet_header = EthernetHeader(dst_mac=PEV_MAC, src_mac=evse_mac)
    homeplug_header = HomePlugHeader(CM_ATTEN_CHAR | MMTYPE_IND)
    atten_car = AtennChar(
        source_address=PEV_MAC,
        run_id=RUN_ID,
        source_id=0x00,
        resp_id=0x00,
        num_sounds=num_total_sounds,
        num_groups=num_groups,
        aag=aag,
    )

    atten_car_frame = (
        ethernet_header.pack_big() + homeplug_header.pack_big() + atten_car.pack_big()
    )

    # Slac Atten Char Response payload
    ethernet_header = EthernetHeader(dst_mac=evse_mac, src_mac=PEV_MAC)
    homeplug_header = HomePlugHeader(CM_ATTEN_CHAR | MMTYPE_RSP)
    atten_car_rsp = AtennCharRsp(
        source_address=PEV_MAC, run_id=RUN_ID, source_id=0x00, resp_id=0x00, result=0x00
    )

    atten_car_rsp_frame = (
        ethernet_header.pack_big()
        + homeplug_header.pack_big()
        + atten_car_rsp.pack_big()
    )
    with patch(
        "pyslac.session.readeth", new=AsyncMock(return_value=atten_car_rsp_frame)
    ):
        evse_slac_session.send_frame = AsyncMock()
        # Fake that we already received these parameters before, during
        # SLAC Param message sequence
        evse_slac_session.application_type = SLAC_APPLICATION_TYPE
        evse_slac_session.security_type = SLAC_SECURITY_TYPE

        evse_slac_session.pev_mac = PEV_MAC
        evse_slac_session.evse_mac = evse_mac
        evse_slac_session.run_id = RUN_ID
        evse_slac_session.num_total_sounds = num_total_sounds
        evse_slac_session.num_groups = num_groups
        evse_slac_session.aag = aag

        await evse_slac_session.cm_atten_char()

        # Test that Slac Atten Charc IND frame was sent
        evse_slac_session.send_frame.assert_called_with(atten_car_frame)

    # Force an Error on getting the Slac Chara Atten Response, by changing
    # the Response result to 0x01
    atten_car_rsp.result = 0x01
    atten_car_rsp_frame = (
        ethernet_header.pack_big()
        + homeplug_header.pack_big()
        + atten_car_rsp.pack_big()
    )
    with patch(
        "pyslac.session.readeth", new=AsyncMock(return_value=atten_car_rsp_frame)
    ):
        with pytest.raises(ValueError):
            await evse_slac_session.cm_atten_char()
            assert evse_slac_session.state == STATE_UNMATCHED

    # Force an Error by changing the run_id
    atten_car_rsp.run_id = b"\xAA" * 8
    atten_car_rsp_frame = (
        ethernet_header.pack_big()
        + homeplug_header.pack_big()
        + atten_car_rsp.pack_big()
    )
    with patch(
        "pyslac.session.readeth", new=AsyncMock(return_value=atten_car_rsp_frame)
    ):
        with pytest.raises(ValueError):
            await evse_slac_session.cm_atten_char()
            assert evse_slac_session.state == STATE_UNMATCHED


@pytest.mark.asyncio
async def test_slac_match(evse_slac_session, evse_mac):
    """
    Tests Slac Match step
    """
    # Slac Match  payload
    ethernet_header = EthernetHeader(dst_mac=evse_mac, src_mac=PEV_MAC)
    homeplug_header = HomePlugHeader(CM_SLAC_MATCH | MMTYPE_REQ)
    slac_match_req = MatchReq(pev_mac=PEV_MAC, evse_mac=evse_mac, run_id=RUN_ID)

    slac_match_req_frame = (
        ethernet_header.pack_big()
        + homeplug_header.pack_big()
        + slac_match_req.pack_big()
    )

    with patch(
        "pyslac.session.readeth", new=AsyncMock(return_value=slac_match_req_frame)
    ):
        # mock of the send_frame routine
        evse_slac_session.send_frame = AsyncMock()
        # mocking of data that is set in previous steps
        evse_slac_session.run_id = RUN_ID

        # Slac Confirmation Message
        evse_slac_session.evse_mac = evse_mac
        evse_slac_session.nid = QUALCOMM_NID
        evse_slac_session.nmk = QUALCOMM_NMK
        ethernet_header = EthernetHeader(dst_mac=PEV_MAC, src_mac=evse_mac)
        homeplug_header = HomePlugHeader(CM_SLAC_MATCH | MMTYPE_CNF)
        slac_match_conf = MatchCnf(
            pev_mac=PEV_MAC,
            evse_mac=evse_mac,
            run_id=RUN_ID,
            nid=QUALCOMM_NID,
            nmk=QUALCOMM_NMK,
        )

        frame_to_send = (
            ethernet_header.pack_big()
            + homeplug_header.pack_big()
            + slac_match_conf.pack_big()
        )

        await evse_slac_session.cm_slac_match()

        assert evse_slac_session.pev_mac == PEV_MAC
        assert evse_slac_session.pev_id == 0x00
        # Slac Match Cnf test
        evse_slac_session.send_frame.assert_called_with(frame_to_send)
        assert evse_slac_session.state == STATE_MATCHED

        #  Force an Error
        with pytest.raises(ValueError):
            # force a different run id to trigger an error
            evse_slac_session.run_id = b"\xAA" * 8
            await evse_slac_session.cm_slac_match()
