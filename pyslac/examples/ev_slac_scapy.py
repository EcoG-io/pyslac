from time import sleep

from scapy.all import (
    Ether,
    Packet,
    X3BytesField,
    XByteField,
    XIntField,
    XLEShortField,
    XNBytesField,
    XShortField,
    sendp,
)

from pyslac.enums import (
    CM_ATTEN_CHAR,
    CM_ATTEN_PROFILE,
    CM_MNBC_SOUND,
    CM_SET_KEY,
    CM_SLAC_MATCH,
    CM_SLAC_PARM,
    CM_START_ATTEN_CHAR,
    ETH_TYPE_HPAV,
    MMTYPE_CNF,
    MMTYPE_IND,
    MMTYPE_REQ,
    MMTYPE_RSP,
    SLAC_SETTLE_TIME,
)
from pyslac.utils import get_if_hwaddr

BROADCAST_ADDR = "FF:FF:FF:FF:FF:FF"
ATHEROS_CHIP_MAC = "00:b0:52:00:00:01"
IFACE = "enp0s3"


class HomePlugHeader(Packet):
    name = "HomePlugHeader "
    fields_desc = [
        XByteField("mmv", 1),
        XLEShortField("mm_type", CM_SET_KEY | MMTYPE_REQ),
        XByteField("fmsn", 0),
        XByteField("fmid", 0),
    ]


class SetKeyRequest(Packet):
    name = "SetKeyRequest Payload "
    fields_desc = [
        XByteField("key_type", 1),
        XIntField("my_nonce", 0xAAAAAAAA),
        XIntField("your_nonce", 0x00000000),
        XByteField("pid", 4),
        XShortField("prn", 0x0000),
        XByteField("pmn", 0),
        XByteField("cco_cap", 0),
        XIntField("nid_first_4_bytes", 0x026BCBA5),
        X3BytesField("nid_last_3bytes", 0x354E08),
        XByteField("new_eks", 1),
        XNBytesField("new_key", 0xB59319D7E8157BA001B018669CCEE30D, 16),
        X3BytesField("rsvd", 0x000000),
    ]


class SetKeyConfirmation(Packet):
    name = "SetKeyResponse Payload "
    fields_desc = [
        XByteField("result", 0),
        XIntField("my_nonce", 0xAAAAAAAA),
        XIntField("your_nonce", 0x00000000),
        XByteField("pid", 4),
        XShortField("prn", 0x0000),
        XByteField("pmn", 0),
        XByteField("cco_cap", 0),
        XNBytesField("rsvd", 0, 27),
    ]


# EV Messages to Send
class SlacParmReq(Packet):
    name = "Slac Parm Req Payload "
    fields_desc = [
        XByteField("application_type", 0x00),
        XByteField("security_type", 0x00),
        XNBytesField("run_id", 0, 8),
        XNBytesField("rsvd", 0, 31),
    ]


class StartAttenChar(Packet):
    name = "Start Atten Characterization Payload "
    fields_desc = [
        XByteField("application_type", 0x00),
        XByteField("security_type", 0x00),
        XByteField(
            "num_sounds", 2
        ),  # This defines the number of sounds that the EV will send to the EVSE.
        # And overrides the expected sounds defined by enum SLAC_MSOUNDS
        XByteField(
            "time_out", 100
        ),  # This defines the time to 10 secs (100 * 100 ms) that the EV must
        # deliver the mnbc sounds before the EVSE times out
        XByteField("resp_type", 0x01),
        XNBytesField("forwarding_sta", 0, 6),
        XNBytesField("run_id", 0, 8),
        XNBytesField("rsvd", 0, 22),
    ]


class MnbcSound(Packet):
    name = "MnbcSound Payload "
    fields_desc = [
        XByteField("application_type", 0x00),
        XByteField("security_type", 0x00),
        XNBytesField("sender_id", 0, 17),
        XByteField("cnt", 2),
        XNBytesField("run_id", 0, 8),
        XNBytesField("rsvd", 0, 8),
        XNBytesField("rnd", 0, 16),
    ]


class AttenProfile(Packet):
    name = "Atten Profile Payload "
    fields_desc = [
        XNBytesField("pev_mac", 0, 6),
        XByteField("num_groups", 3),
        XByteField("rsvd", 0),
        XByteField("aag1", 40),
        XByteField("aag2", 36),
        XByteField("aag3", 40),
        XNBytesField("rsvd1", 0, 60 - 30),
    ]


class AttenCharResp(Packet):
    name = "Start Atten Characterization Payload "
    fields_desc = [
        XByteField("application_type", 0x00),
        XByteField("security_type", 0x00),
        XNBytesField("source_address", 0, 6),
        XNBytesField("run_id", 0, 8),
        XNBytesField("source_id", 0, 17),
        XNBytesField("resp_id", 0, 17),
        XByteField("result", 0),
    ]


class SlacMatch(Packet):
    name = "Slac Match Request Payload "
    fields_desc = [
        XByteField("application_type", 0x00),
        XByteField("security_type", 0x00),
        XNBytesField("mvf_length", 0x003E, 2),
        XNBytesField("pev_id", 0, 17),
        XNBytesField("pev_mac", 0, 6),
        XNBytesField("evse_id", 0, 17),
        XNBytesField("evse_mac", 0, 6),
        XNBytesField("run_id", 0, 8),
        XNBytesField("rsvd", 0, 8),
    ]


host_mac = get_if_hwaddr(IFACE, to_mac_fmt=True)
host_mac_bytes = get_if_hwaddr(IFACE, to_mac_fmt=False)
host_mac_int = int.from_bytes(host_mac_bytes, "big")
eth_header = Ether(src=host_mac, dst=ATHEROS_CHIP_MAC, type=ETH_TYPE_HPAV)


homeplug_header = HomePlugHeader()
set_key_request = SetKeyRequest()
frame_rsp = eth_header / homeplug_header / set_key_request

# we can use this way of padding or the rsvd field
# padstr = '\x00' * (60 - len(eth_header) - len(homeplug_header) - len(key_request_payload))  # noqa: E501
# pad = Padding(load=padstr) # a bunch of 0-bytes
# frame = eth_header/homeplug_header/set_key_request/pad

# SetKey CNF
homeplug_header.mm_type = CM_SET_KEY | MMTYPE_CNF
set_key_confirmation = SetKeyConfirmation()
frame_rsp = eth_header / homeplug_header / set_key_confirmation
sendp(frame_rsp, iface=IFACE)
# We need to wait SLAC_SETTLE_TIME because is the time the EVSE will wait
# after receiving the SET_KEY_CNF for the HLE to settle. In a real EV
# simulator, this wouldnt be  needed
sleep(SLAC_SETTLE_TIME)
# Slac Parm Req
homeplug_header.mm_type = CM_SLAC_PARM | MMTYPE_REQ
eth_header.dst = BROADCAST_ADDR
slac_parm_req = SlacParmReq()
frame_rsp = eth_header / homeplug_header / slac_parm_req
sleep(10)
sendp(frame_rsp, iface=IFACE)

# Start Atten Char
homeplug_header.mm_type = CM_START_ATTEN_CHAR | MMTYPE_IND
eth_header.dst = BROADCAST_ADDR
start_atten_char = StartAttenChar()
frame_rsp = eth_header / homeplug_header / start_atten_char
# The EV may send 3 start atten char, but the QCA chip will forward only 1
# to the application
sendp(frame_rsp, iface=IFACE)

# MNBC Sound
# Send 2 times, since we defined 2 num of sounds in StartAttenChar
homeplug_header.mm_type = CM_MNBC_SOUND | MMTYPE_IND
eth_header.dst = BROADCAST_ADDR
ev_cm_mnbc_sound = MnbcSound()
frame_rsp_mnbc = eth_header / homeplug_header / ev_cm_mnbc_sound

# AttenProfile
#  Send 2 times, since we defined 2 num of sounds in StartAttenChar
homeplug_header.mm_type = CM_ATTEN_PROFILE | MMTYPE_IND
eth_header.src = ATHEROS_CHIP_MAC
eth_header.dst = host_mac
atten_profile = AttenProfile(pev_mac=host_mac_int)
frame_rsp_atten = eth_header / homeplug_header / atten_profile

sendp(frame_rsp_mnbc, iface=IFACE)
sleep(0.1)
sendp(frame_rsp_atten, iface=IFACE)
sleep(0.1)
sendp(frame_rsp_mnbc, iface=IFACE)
sleep(0.1)
sendp(frame_rsp_atten, iface=IFACE)
sleep(0.1)


# EV Receives a Atten Char Indicator and shall respond with Response
# Unicast
homeplug_header.mm_type = CM_ATTEN_CHAR | MMTYPE_RSP
eth_header.src = host_mac
eth_header.dst = host_mac
atten_char_rsp = AttenCharResp(source_address=host_mac_int)
frame_rsp = eth_header / homeplug_header / atten_char_rsp
sendp(frame_rsp, iface=IFACE)
sleep(0.2)


# EV does the Atten threshold calculation and evaluation, then sends a Match
homeplug_header.mm_type = CM_SLAC_MATCH | MMTYPE_REQ
slac_match = SlacMatch(pev_mac=host_mac_int, evse_mac=host_mac_int)
frame_rsp = eth_header / homeplug_header / slac_match
sendp(frame_rsp, iface=IFACE)
# Then the EV Should receive a MAtch conf with the NMK and NID so he can
# join the network
