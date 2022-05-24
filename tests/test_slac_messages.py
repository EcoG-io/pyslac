from pyslac.enums import (
    BROADCAST_ADDR,
    CM_SET_CCO_CAPAB,
    CM_SET_KEY_MY_NONCE,
    CM_SET_KEY_NEW_EKS,
    CM_SET_KEY_PID,
    CM_SET_KEY_PMN,
    CM_SET_KEY_PRN,
    CM_SET_KEY_TYPE,
    CM_SET_KEY_YOUR_NONCE,
    SLAC_APPLICATION_TYPE,
    SLAC_ATTEN_TIMEOUT,
    SLAC_MSOUNDS,
    SLAC_RESP_TYPE,
    SLAC_SECURITY_TYPE,
)
from pyslac.messages import (
    AtennChar,
    AtennCharRsp,
    AttenProfile,
    MatchCnf,
    MatchReq,
    MnbcSound,
    SetKeyCnf,
    SetKeyReq,
    SlacParmCnf,
    SlacParmReq,
    StartAtennChar,
)

PRE_PADDING = b"\x00" * 19
RUN_ID = b"\x00\x01" * 4
PEV_MAC = b"\xAA" * 6
EVSE_MAC = b"\xAB" * 6
# HomePlugAV0123 (defined in evse.c and also evse.ini)
EVSE_NMK = b"\xb5\x93\x19\xd7\xe8\x15\x7b\xa0\x01\xb0\x18\x66\x9c\xce\xe3\x0d"
# HomePlugAV0123 (defined in evse.c and also evse.ini)
EVSE_NID = b"\x02\x6b\xcb\xa5\x35\x4e\x08"


def test_set_key_request():
    test_set_key = SetKeyReq(nid=EVSE_NID, new_key=EVSE_NMK)
    set_key_bytes = test_set_key.pack_big()
    expected_bytes = (
        CM_SET_KEY_TYPE
        + CM_SET_KEY_MY_NONCE
        + CM_SET_KEY_YOUR_NONCE
        + CM_SET_KEY_PID
        + CM_SET_KEY_PRN
        + CM_SET_KEY_PMN
        + CM_SET_CCO_CAPAB
        + EVSE_NID
        + CM_SET_KEY_NEW_EKS
        + EVSE_NMK
    )
    assert set_key_bytes == expected_bytes


def test_set_key_response():
    result = b"\x00"
    set_key_response_bytes = (
        PRE_PADDING
        + result
        + CM_SET_KEY_MY_NONCE
        + CM_SET_KEY_YOUR_NONCE
        + CM_SET_KEY_PID
        + CM_SET_KEY_PRN
        + CM_SET_KEY_PMN
        + CM_SET_CCO_CAPAB
        + b"\x00" * 27
    )

    set_key_cnf = SetKeyCnf.from_bytes(set_key_response_bytes)

    assert set_key_cnf.my_nonce == CM_SET_KEY_MY_NONCE


def test_slac_parm_req():

    set_key_response_bytes = (
        PRE_PADDING
        + SLAC_APPLICATION_TYPE.to_bytes(1, "big")
        + SLAC_SECURITY_TYPE.to_bytes(1, "big")
        + RUN_ID
    )

    slac_parm_req = SlacParmReq.from_bytes(set_key_response_bytes)

    assert slac_parm_req.run_id == RUN_ID
    assert slac_parm_req.application_type == SLAC_APPLICATION_TYPE
    assert slac_parm_req.security_type == SLAC_SECURITY_TYPE


def test_slac_parm_cnf():

    slac_parm_cnf = SlacParmCnf(forwarding_sta=PEV_MAC, run_id=RUN_ID)
    slac_parm_bytes = slac_parm_cnf.pack_big()
    expected_bytes = (
        BROADCAST_ADDR
        + SLAC_MSOUNDS.to_bytes(1, "big")
        + SLAC_ATTEN_TIMEOUT.to_bytes(1, "big")
        + SLAC_RESP_TYPE.to_bytes(1, "big")
        + PEV_MAC
        + SLAC_APPLICATION_TYPE.to_bytes(1, "big")
        + SLAC_SECURITY_TYPE.to_bytes(1, "big")
        + RUN_ID
    )
    assert slac_parm_bytes == expected_bytes


def test_start_atten_char():
    #  StartAttenChar from bytes test
    start_atten_char_bytes = (
        PRE_PADDING
        + SLAC_APPLICATION_TYPE.to_bytes(1, "big")
        + SLAC_SECURITY_TYPE.to_bytes(1, "big")
        + SLAC_MSOUNDS.to_bytes(1, "big")
        + SLAC_ATTEN_TIMEOUT.to_bytes(1, "big")
        + SLAC_RESP_TYPE.to_bytes(1, "big")
        + PEV_MAC
        + RUN_ID
    )

    start_atten_char = StartAtennChar.from_bytes(start_atten_char_bytes)

    assert start_atten_char.run_id == RUN_ID
    assert start_atten_char.application_type == SLAC_APPLICATION_TYPE
    assert start_atten_char.security_type == SLAC_SECURITY_TYPE
    assert start_atten_char.num_sounds == SLAC_MSOUNDS
    assert start_atten_char.time_out == SLAC_ATTEN_TIMEOUT
    assert start_atten_char.forwarding_sta == PEV_MAC
    assert start_atten_char.resp_type == SLAC_RESP_TYPE

    # StartAttenChar Constructor

    start_atten_char_req = StartAtennChar(
        num_sounds=SLAC_MSOUNDS,
        time_out=SLAC_ATTEN_TIMEOUT,
        forwarding_sta=PEV_MAC,
        run_id=RUN_ID,
    )
    assert start_atten_char_req.run_id == RUN_ID
    assert start_atten_char_req.application_type == SLAC_APPLICATION_TYPE
    assert start_atten_char_req.security_type == SLAC_SECURITY_TYPE
    assert start_atten_char_req.num_sounds == SLAC_MSOUNDS
    assert start_atten_char_req.time_out == SLAC_ATTEN_TIMEOUT
    assert start_atten_char_req.forwarding_sta == PEV_MAC
    assert start_atten_char_req.resp_type == SLAC_RESP_TYPE


def test_mnbc_sound():
    #  MNBC Sound from bytes test
    cnt = SLAC_MSOUNDS.to_bytes(1, "big")
    sender_id = b"\x00" * 17
    rsvd = b"\x00" * 8
    random = 0xFA
    mnbc_sound_bytes = (
        PRE_PADDING
        + SLAC_APPLICATION_TYPE.to_bytes(1, "big")
        + SLAC_SECURITY_TYPE.to_bytes(1, "big")
        + sender_id
        + cnt
        + RUN_ID
        + rsvd
        + random.to_bytes(16, "big")
    )

    mnbc_sound = MnbcSound.from_bytes(mnbc_sound_bytes)

    assert mnbc_sound.run_id == RUN_ID
    assert mnbc_sound.application_type == SLAC_APPLICATION_TYPE
    assert mnbc_sound.security_type == SLAC_SECURITY_TYPE
    assert mnbc_sound.cnt == SLAC_MSOUNDS
    assert mnbc_sound.sender_id == int.from_bytes(sender_id, "big")
    assert mnbc_sound.rsvd == int.from_bytes(rsvd, "big")
    assert mnbc_sound.rnd == random

    # MNBC Sound Constructor

    mnbc_sound_req = MnbcSound(cnt=SLAC_MSOUNDS, run_id=RUN_ID, rnd=random)
    assert mnbc_sound_req.run_id == RUN_ID
    assert mnbc_sound_req.application_type == SLAC_APPLICATION_TYPE
    assert mnbc_sound_req.security_type == SLAC_SECURITY_TYPE
    assert mnbc_sound_req.cnt == SLAC_MSOUNDS
    assert mnbc_sound_req.sender_id == int.from_bytes(sender_id, "big")
    assert mnbc_sound_req.rsvd == int.from_bytes(rsvd, "big")
    assert mnbc_sound_req.rnd == random


def test_atten_profile():
    # Atten Profile from_bytes
    aag_group = [20, 30, 10]
    num_groups = 0x03
    aag_bytes = b""
    rsvd = b"\x00"
    for group in range(num_groups):
        aag_bytes += aag_group[group].to_bytes(1, "big")

    atten_profile_bytes = (
        PRE_PADDING + PEV_MAC + num_groups.to_bytes(1, "big") + rsvd + aag_bytes
    )

    atten_profile = AttenProfile.from_bytes(atten_profile_bytes)

    assert atten_profile.num_groups == num_groups
    assert atten_profile.aag == aag_group
    assert atten_profile.pev_mac == PEV_MAC

    #  AttenProfile Constructor
    atten_profile_req = AttenProfile(
        pev_mac=PEV_MAC, aag=aag_group, num_groups=num_groups
    )
    assert atten_profile_req.num_groups == num_groups
    assert atten_profile_req.aag == aag_group
    assert atten_profile_req.pev_mac == PEV_MAC


def test_atten_char():
    # Atten Characterisation from_bytes
    aag_group = [20, 30, 10]
    num_groups = 0x03
    source_id = 0x00
    resp_id = 0x00
    atten_char_bytes = (
        PRE_PADDING
        + SLAC_APPLICATION_TYPE.to_bytes(1, "big")
        + SLAC_SECURITY_TYPE.to_bytes(1, "big")
        + PEV_MAC
        + RUN_ID
        + source_id.to_bytes(17, "big")
        + resp_id.to_bytes(17, "big")
        + SLAC_MSOUNDS.to_bytes(1, "big")
        + num_groups.to_bytes(1, "big")
        + bytearray(aag_group)
    )

    atten_char = AtennChar.from_bytes(atten_char_bytes)

    assert atten_char.application_type == SLAC_APPLICATION_TYPE
    assert atten_char.security_type == SLAC_SECURITY_TYPE
    assert atten_char.source_address == PEV_MAC
    assert atten_char.run_id == RUN_ID
    assert atten_char.source_id == source_id
    assert atten_char.resp_id == source_id
    assert atten_char.num_sounds == SLAC_MSOUNDS
    assert atten_char.num_groups == num_groups
    assert atten_char.aag == aag_group

    # Atten Characterisation Constructor
    atten_char_req = AtennChar(
        source_address=PEV_MAC,
        run_id=RUN_ID,
        source_id=source_id,
        resp_id=resp_id,
        num_sounds=SLAC_MSOUNDS,
        num_groups=num_groups,
        aag=aag_group,
    )
    assert atten_char_req.application_type == SLAC_APPLICATION_TYPE
    assert atten_char_req.security_type == SLAC_SECURITY_TYPE
    assert atten_char_req.source_address == PEV_MAC
    assert atten_char_req.run_id == RUN_ID
    assert atten_char_req.source_id == source_id
    assert atten_char_req.resp_id == resp_id
    assert atten_char_req.num_sounds == SLAC_MSOUNDS
    assert atten_char_req.num_groups == num_groups
    assert atten_char_req.aag == aag_group


def test_atten_char_resp():
    # Atten Characterisation Response from_bytes
    # aag_group = [20, 30, 10]
    # num_groups = 0x03
    source_id = 0x00
    resp_id = 0x00
    result = 0x00
    atten_char_resp_bytes = (
        PRE_PADDING
        + SLAC_APPLICATION_TYPE.to_bytes(1, "big")
        + SLAC_SECURITY_TYPE.to_bytes(1, "big")
        + PEV_MAC
        + RUN_ID
        + source_id.to_bytes(17, "big")
        + resp_id.to_bytes(17, "big")
        + result.to_bytes(1, "big")
    )

    atten_char_resp = AtennCharRsp.from_bytes(atten_char_resp_bytes)

    assert atten_char_resp.application_type == SLAC_APPLICATION_TYPE
    assert atten_char_resp.security_type == SLAC_SECURITY_TYPE
    assert atten_char_resp.source_address == PEV_MAC
    assert atten_char_resp.run_id == RUN_ID
    assert atten_char_resp.source_id == source_id
    assert atten_char_resp.resp_id == source_id
    assert atten_char_resp.result == result

    # Atten Characterisation Response Constructor
    atten_char_resp_constr = AtennCharRsp(
        source_address=PEV_MAC,
        run_id=RUN_ID,
        source_id=source_id,
        resp_id=resp_id,
        result=result,
    )
    assert atten_char_resp_constr.application_type == SLAC_APPLICATION_TYPE
    assert atten_char_resp_constr.security_type == SLAC_SECURITY_TYPE
    assert atten_char_resp_constr.source_address == PEV_MAC
    assert atten_char_resp_constr.run_id == RUN_ID
    assert atten_char_resp_constr.source_id == source_id
    assert atten_char_resp_constr.resp_id == resp_id
    assert atten_char_resp_constr.result == result


def test_match_req():
    # Match Request from_bytes
    mvf_length = 0x003E
    pev_id = 0x00
    evse_id = 0x00
    rsvd = 0x00
    match_req_bytes = (
        PRE_PADDING
        + SLAC_APPLICATION_TYPE.to_bytes(1, "big")
        + SLAC_SECURITY_TYPE.to_bytes(1, "big")
        + mvf_length.to_bytes(2, "big")
        + pev_id.to_bytes(17, "big")
        + PEV_MAC
        + evse_id.to_bytes(17, "big")
        + EVSE_MAC
        + RUN_ID
        + rsvd.to_bytes(8, "big")
    )

    match_req = MatchReq.from_bytes(match_req_bytes)

    assert match_req.application_type == SLAC_APPLICATION_TYPE
    assert match_req.security_type == SLAC_SECURITY_TYPE
    assert match_req.mvf_length == mvf_length
    assert match_req.pev_id == pev_id
    assert match_req.pev_mac == PEV_MAC
    assert match_req.evse_id == evse_id
    assert match_req.evse_mac == EVSE_MAC
    assert match_req.run_id == RUN_ID
    assert match_req.rsvd == rsvd

    # Match Request Constructor
    match_req_constr = MatchReq(pev_mac=PEV_MAC, evse_mac=EVSE_MAC, run_id=RUN_ID)
    assert match_req_constr.application_type == SLAC_APPLICATION_TYPE
    assert match_req_constr.security_type == SLAC_SECURITY_TYPE
    assert match_req_constr.mvf_length == mvf_length
    assert match_req_constr.pev_id == pev_id
    assert match_req_constr.pev_mac == PEV_MAC
    assert match_req_constr.evse_id == evse_id
    assert match_req_constr.evse_mac == EVSE_MAC
    assert match_req_constr.run_id == RUN_ID
    assert match_req_constr.rsvd == rsvd


def test_match_conf():
    # Match Confirmation from_bytes
    mvf_length = 0x56
    pev_id = 0x00
    evse_id = 0x00
    rsvd_1 = 0x00
    rsvd_2 = 0x00
    match_conf_bytes = (
        PRE_PADDING
        + SLAC_APPLICATION_TYPE.to_bytes(1, "big")
        + SLAC_SECURITY_TYPE.to_bytes(1, "big")
        + mvf_length.to_bytes(2, "big")
        + pev_id.to_bytes(17, "big")
        + PEV_MAC
        + evse_id.to_bytes(17, "big")
        + EVSE_MAC
        + RUN_ID
        + rsvd_1.to_bytes(8, "big")
        + EVSE_NID
        + rsvd_2.to_bytes(1, "big")
        + EVSE_NMK
    )

    match_conf = MatchCnf.from_bytes(match_conf_bytes)

    assert match_conf.application_type == SLAC_APPLICATION_TYPE
    assert match_conf.security_type == SLAC_SECURITY_TYPE
    assert match_conf.mvf_length == mvf_length
    assert match_conf.pev_id == pev_id
    assert match_conf.pev_mac == PEV_MAC
    assert match_conf.evse_id == evse_id
    assert match_conf.evse_mac == EVSE_MAC
    assert match_conf.run_id == RUN_ID
    assert match_conf.rsvd_1 == rsvd_1
    assert match_conf.nid == EVSE_NID
    assert match_conf.rsvd_2 == rsvd_2
    assert match_conf.nmk == EVSE_NMK

    # Match Confirmation request
    match_conf_req = MatchCnf(
        pev_mac=PEV_MAC, evse_mac=EVSE_MAC, run_id=RUN_ID, nid=EVSE_NID, nmk=EVSE_NMK
    )
    assert match_conf_req.application_type == SLAC_APPLICATION_TYPE
    assert match_conf_req.security_type == SLAC_SECURITY_TYPE
    assert match_conf_req.mvf_length == mvf_length
    assert match_conf_req.pev_id == pev_id
    assert match_conf_req.pev_mac == PEV_MAC
    assert match_conf_req.evse_id == evse_id
    assert match_conf_req.evse_mac == EVSE_MAC
    assert match_conf_req.run_id == RUN_ID
    assert match_conf_req.rsvd_1 == rsvd_1
    assert match_conf_req.nid == EVSE_NID
    assert match_conf_req.rsvd_2 == rsvd_2
    assert match_conf_req.nmk == EVSE_NMK
