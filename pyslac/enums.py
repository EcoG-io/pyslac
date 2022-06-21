from enum import Enum

# [V2G3-M06-05]- In case NO communication could be established with a
# 5 % control pilot duty cycle (matching process not started), if the EVSE
# wants to switch to a nominal duty cycle, then the change from 5 % to a
# nominal duty cycle shall be done with a specific sequence
# B2 or C2 (5 %) -> E or F -> B2 (nominal value) to allow backward
# compatibility. The minimum time at the control pilot state E or F is
# defined by T_step_EF.

# [V2G3-M06-06] In case a communication has already been established within
# 5 % control pilot duty cycle (“Matched state” reached or
# matching process ongoing), a change from 5 % to a nominal duty cycle shall be
# done with a X1 state in the middle (minimum time as defined in [IEC-3]
# Seq 9.2), to signal the EV that the control pilot duty cycle will change to a
# nominal duty cycle

# [V2G3 M06-07] - If an AC EVSE applies a 5 % control pilot duty cycle,
# and the EVSE receives NO SLAC request within TT_EVSE_SLAC_init, the EVSE
# shall go to state E or F for T_step_EF (min 4 s), shall go back to 5 % duty
# cycle, and  shall reset the TT_EVSE_SLAC_init timeout before being ready to
# answer a matching request again. This sequence shall be retried
# C_sequ_retry times (2). At the end, without any reaction, the EVSE shall go
# to state X1

# [V2G3-M06-08] After positive EIM, if no matching process is running, the EVSE
# shall signal control pilot state E/F for T_step_EF, then signal control pilot
# state X1/X2 (nominal).

# [V2G3 -M06-09] If a control pilot state E/F -> Bx, Cx, Dx transition is used
# for triggering retries or legacy issues, the state E/F shall be at least
# T_step_EF.

# [V2G2-852] - If no positive authorization information from an EIM has been
# received the EVSE shall apply PWM equal to 5 %.

# [V2G2-853] - If an EVSE receives positive authorization information from an
# EIM the EVSE shall apply a nominal duty cycle.

# [V2G2-931] - The EVSE shall signal a PWM of 5 % or nominal duty cycle after
# sending the message AuthorizationRes.


class Timers(float, Enum):
    """
    Timeouts defined by ISO15118-3 in table A.1
    All times are in seconds
    """

    # Time between the moment the EVSE detects state B and the reception of the
    # first SLAC Message, i.e. CM_SLAC_PARM.REQ.
    # This Timer is actually set in the environment.py, for debugging and
    # development reasons, allowing a easier setting of the time with the
    # docker-compose.dev.yml
    SLAC_INIT_TIMEOUT = 50.0  # [TT_EVSE_SLAC_init=20 s - 50 s]

    # Timeout for the reception of either CM_VALIDATE.REQ or CM_SLAC_MATCH.REQ
    # message, after reception of CM_ATTEN_CHAR.RSP
    SLAC_MATCH_TIMEOUT = 10.0  # [TT_EVSE_match_session=10 s]

    # Time the EV shall wait for CM_ATTEN_CHAR.IND after sending the first
    # CM_START_ATTEN_CHAR.IND
    SLAC_ATTEN_RESULTS_TIMEOUT = 1.2  # [TT_EV_atten_results = 1200 ms]

    # Timeout used for awaiting for a Request
    SLAC_REQ_TIMEOUT = 0.4  # [TT_match_sequence = 400 ms]

    # Timeout used for awaiting for a Response
    SLAC_RESP_TIMEOUT = 0.2  # [TT_match_response = 200 ms]

    # According to the standard:
    # [V2G3-A09-124] - In case the matching process is considered as FAILED,
    # wait for a time of TT_ matching_rate before restarting the process.

    # [V2G3-A09-125] - If the matching process fails for all retries started
    # within TT_matching_repetition, the matching process shall be stopped
    # in “Unmatched” state (see Figure 11).

    # The number maximum of retries is defined by C_conn_max_match = min 3
    # So, if within the TT_matching_repetition (10 s) time, the number of
    # retries expires, the matching process shall be stopped
    # in “Unmatched” state. (ISO Requirement couldnt be found for this,
    # but this is the logical steps to do)

    # Total time while the new SLAC repetitions can happen.
    # Once this timer is expired, the Matching process is considered FAILED
    SLAC_TOTAL_REPETITIONS_TIMEOUT = 10.0  # [TT_matching_repetition = 10 s]

    # Time to wait for the repetition of the matching process
    SLAC_REPETITION_TIMEOUT = 0.4  # [TT_matching_rate = 400 ms]

    # Time required to await while in state E or F (used in some use cases,
    # like the one defined by [V2G3 M06-07])
    SLAC_E_F_TIMEOUT = 4.0  # [T_step_EF = min 4 s]


# Timeout on the EVSE side that triggers the calculation of the average
# attenuation profile. Time is in multiples of 100 ms. In this case, we have
# 600 ms (6 * 100)

# Timers.SLAC_ATTEN_TIMEOUT is the only value in the Timers class that its use
# is supposed to be done as an integer (type int)
SLAC_ATTEN_TIMEOUT = 6  # [TT_EVSE_match_MNBC = 600 ms]


class FramesSizes(int, Enum):
    """
    Frames Sizes in bytes of several messages
    (currently only EVSE side relevant ones)

    The size is calculated as the summation of the size of:
    * EthernetHeader = 14 bytes
    * HomePlugHeader = 5 bytes
    * MessageSize = X bytes

    For example, a complete CM_ATTEN_CHAR.RSP frame must have 70 Bytes:
    EthernetHeader = 14 bytes
    HomePlugHeader  = 5 bytes
    AttenCharRsp = 51 bytes

    CM_MNBC_SOUND.IND and CM_ATTEN_PROFILE.IND are not included
    """

    CM_SET_KEY_CNF = 60
    CM_SLAC_PARM_REQ = 60
    CM_START_ATTEN_CHAR_IND = 60
    CM_MNBC_SOUND_IND = 71
    CM_ATTEN_PROFILE_IND = 85
    CM_ATTEN_CHAR_RSP = 70
    CM_SLAC_MATCH_REQ = 85
    LINK_STATUS_CNF = 60


# Socket Receive buffer max frame is equal to the MAX ETH Frame Size
BUFF_MAX_SIZE = 1500
SLAC_RUNID_LEN = 8
# NumberOfSounds
SLAC_MSOUNDS = 10

# 15118-3 mentions the RESP_TYPE shall be 0x01 indicating other GP Stations
# However, qualcomm example uses 0x00 which indicates the recipient of the
# SOUND MPDUs shall communicate the signal attenuation characteristic profile
# data to the HLE instead of another GP STA.
SLAC_RESP_TYPE = 0x01
SLAC_APPLICATION_TYPE = 0x00
SLAC_SECURITY_TYPE = 0x00

# Pause used between sounds sent by the ev during cm_mnbc_sound routine
# By the spec can be a value between 20 and 50 ms (TP_EV_batch_msg_interval)
SLAC_PAUSE = 0.02
SLAC_GROUPS = 58
SLAC_LIMIT = 40
# Time to await after reception of a successful CM_SET_KEY.CNF
# This timer is used and defined in the Qualcomm example
SLAC_SETTLE_TIME = 10

ETHER_ADDR_LEN = 6
BROADCAST_ADDR = b"\xFF" * 6


CM_SET_KEY_TYPE = b"\x01"
# According to 15118-3 this value should be 0x00 and not 0xAA
CM_SET_KEY_MY_NONCE = b"\xaa\xaa\xaa\xaa"
# CM_SET_KEY_MY_NONCE = b'\x00' * 4
CM_SET_KEY_YOUR_NONCE = b"\x00\x00\x00\x00"
CM_SET_KEY_PID = b"\x04"
CM_SET_KEY_PRN = b"\x00\x00"
CM_SET_KEY_PMN = b"\x00"
CM_SET_KEY_NEW_EKS = b"\x01"
CM_SET_CCO_CAPAB = b"\x00"

# MMTypes Base Codes
CM_SET_KEY = 0x6008  # Equal to 24584 in decimal
CM_SLAC_PARM = 0x6064
CM_START_ATTEN_CHAR = 0x6068
CM_MNBC_SOUND = 0x6074
CM_ATTEN_PROFILE = 0x6084
CM_ATTEN_CHAR = 0x606C
CM_SLAC_MATCH = 0x607C

# MMType Kind
MMTYPE_REQ = 0x0000
MMTYPE_CNF = 0x0001
MMTYPE_IND = 0x0002
MMTYPE_RSP = 0x0003

# Ehternet Type HomePlug AV
ETH_TYPE_HPAV = 0x88E1

HOMEPLUG_MMV = b"\x01"
HOMEPLUG_FMSN = b"\x00"
HOMEPLUG_FMID = b"\x00"


# STATES
STATE_UNMATCHED = 0
STATE_MATCHING = 1
STATE_MATCHED = 2


# Station Identifier
EVSE_ID = "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"
# The dest MAC was defined in channel.c as follows in Qualcomm open-plc
EVSE_PLC_MAC = b"\x00\xb0\x52\x00\x00\x01"

# Qualcomm settings
# HomePlugAV0123 (defined in evse.c and also evse.ini of Qualcomm open-plc)
QUALCOMM_NID = b"\x02\x6b\xcb\xa5\x35\x4e\x08"
QUALCOMM_NMK = b"\xb5\x93\x19\xd7\xe8\x15\x7b\xa0\x01\xb0\x18\x66\x9c\xce\xe3\x0d"
