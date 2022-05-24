import ctypes
from dataclasses import dataclass
from typing import List

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


@dataclass
class SetKeyReq:
    """
    Associated with CM_SET_KEY.REQ, defined in chapter 11.5.4 of the HPGP
    standard. Check also table page 586, table 11-87

    Also table A.8 from ISO15118-3

    EVSE/PEV -> HPGP Node

    This payload is defined as follows:
    |KeyType|MyNonce|YourNonce|PID|PRN|PMN|CCoCap|NID|NewEKS|NewKey|

    KeyType [1 byte] = 0x01: Fixed value to indicate NMK
    MyNonce [4 bytes] = 0x00000000: Fixed value, used by the emitter of the
                                    message and fixed over one session.
                                    If in another message, the receiver receives
                                    a different value, then it may consider
                                    that the communication was compromised
    YourNonce [4 bytes] = 0x00000000: Fixed value, encrypted payload not used.
                                      This field has the same rationale as
                                      MyNonce but in the opposite direction
                                      of the communication
    PID [1 byte] = 0x04: Fixed value to indicate "HLE protocol"
    PRN [2 bytes] = 0x0000: Fixed value, encrypted payload not used
    PMN [1 byte] = 0x00: Fixed value, encrypted payload not used
    CCo Capability [1 byte] = 0x00 : CCo Capability according to station role;
                                     Ususally the value is variable, but is used
    NID [7 bytes]: 54 LSBs contain the Network identifier and the rest is 0b00
                   Network ID derived from the NMK by the EVSE according to
                   [HPGP], 4.4.3.1
    NewEKS [1 byte] = 0x01: Fixed value to indicate NMK

    NewKey [16 bytes]: NMK (Network Mask, random value per session)

    Message size is = 44 bytes
    """

    # 7bytes
    nid: bytes
    # 16 bytes
    new_key: bytes

    def __bytes__(self, endianess: str = "big"):
        if endianess == "big":
            return (
                CM_SET_KEY_TYPE
                + CM_SET_KEY_MY_NONCE
                + CM_SET_KEY_YOUR_NONCE
                + CM_SET_KEY_PID
                + CM_SET_KEY_PRN
                + CM_SET_KEY_PMN
                + CM_SET_CCO_CAPAB
                + self.nid
                + CM_SET_KEY_NEW_EKS
                + self.new_key
            )
        return (
            self.new_key
            + CM_SET_KEY_NEW_EKS
            + self.nid
            + CM_SET_CCO_CAPAB
            + CM_SET_KEY_PMN
            + CM_SET_KEY_PRN
            + CM_SET_KEY_PID
            + CM_SET_KEY_YOUR_NONCE
            + CM_SET_KEY_MY_NONCE
            + CM_SET_KEY_TYPE
        )

    def pack_big(self):
        return self.__bytes__()

    def pack_little(self):
        return self.__bytes__("little")


@dataclass
class SetKeyCnf:
    """
    Associated with CM_SET_KEY.CNF, defined in chapter 11.5.5 of the HPGP
    standard. Check also table page 586, table 11-87

    Also table A.8 from ISO15118-3

    HPGP Node -> EVSE/PEV

    This payload is defined as follows:
    |Result|MyNonce|YourNonce|PID|PRN|PMN|CCoCap|

    Result [1 byte]: 0x00 - Success, 0x01 - Failure
    MyNonce [4 bytes]: Random number that will be used to verify next message
                       from other end; in encrypted portion of payload.
    YourNonce [4 bytes]: Last nonce received from recipient; it will be used
                         by recipient to verify this message;
                         in encrypted portion of payload.
    PID [1 byte]: Protocol for which Set Key is confirmed
    PRN [2 bytes]: Protocol Run Number (refer to Section 11.5.2.4)
    PMN [1 byte]: Protocol Message Number (refer to Section 11.5.2.5
    CCo Capability [1 byte]: The two LSBs of this field contain the STA’s
                             CCo capability. The interpretation of these bits
                             is the same as in Section 4.4.3.13.4.6.2.
                             The six MSBs of this field are set to 0b000000

    Message size is = 14 bytes
    """

    result: int
    my_nonce: bytes
    your_nonce: bytes
    pid: bytes
    prn: bytes
    pmn: bytes
    cco_capab: bytes

    def __bytes__(self, endianess: str = "big"):
        frame = bytearray(
            self.result.to_bytes(1, "big")
            + self.my_nonce
            + self.your_nonce
            + self.pid
            + self.prn
            + self.pmn
            + self.cco_capab
        )
        if endianess == "big":
            return frame
        return frame.reverse()

    def pack_big(self):
        return self.__bytes__()

    def pack_little(self):
        return self.__bytes__("little")

    @classmethod
    def from_bytes(cls, payload: ctypes) -> "SetKeyCnf":
        # payload: Union[int, bytes]
        # self.result = ctypes.c_uint8(payload[19])
        # The Ethernet and HP header comprise 19 bytes in total
        # result = payload[19]
        #  TODO: Think about pair this with the Homeplug Greenphy Header and
        # check the MMV == HOMEPLUG_MMV and
        # MMType == (CM_SET_KEY | MMTYPE_CNF) fields
        # The result is ignored, because some Qualcomm chips firmware have
        # implemented the wrong logic for it and a result of 0x00 means a
        # failure. In the future we can check if the SET_KEY_REQ was successful
        # by sending a NW_INFO.REQ to check if the NID was really set
        # if result != 0x00:
        #     TODO: Raise SLAC Exception
        #     raise ValueError("Device refused SET_KEY_REQ ")
        return cls(
            result=payload[19],
            my_nonce=payload[20:24],
            your_nonce=payload[24:28],
            pid=payload[28],
            prn=payload[29:31],
            pmn=payload[31],
            cco_capab=payload[32],
        )


@dataclass
class SlacParmReq:
    """
    Broadcast Message
    PEV -> EVSE

    Associated with CM_SLAC_PARM.REQ, defined in chapter 11.5.45 of the HPGP
    standard. Check also table page 586, table 11-87

    Also table A.2 from ISO15118-3

    This payload is defined as follows originally :
    |Application Type|Security Type|Run ID|CipherSuiteSetSize| CipherSuite..

    Application Type [1 byte]: 0x00 Fixed value indicating 'PEV- EVSE matching'
    Security Type [1 bytes]: 0x00 Fixed value indicating 'No Security'
    Run ID [8 bytes]: Identifier for a matching run, randomly chosen by
                      the EV for each CM_SLAC_PARM.REQ message and constant
                      for all following messages of the same run
    CipherSuiteSetSize [1 byte]: Number of supported cipher suites N.
    CipherSuite [1] [2 bytes]: First supported cipher suite.
    CipherSuite [N] [2 bytes]: Nth supported cipher suite.

    However, since Security Type is set as 0x00, Cipher suit is not used, thus
    the payload resumes to:
    |Application Type|Security Type|Run ID|

    Message size is = 10 bytes
    """

    # 8 bytes
    run_id: bytes
    application_type: int = SLAC_APPLICATION_TYPE
    security_type: int = SLAC_SECURITY_TYPE

    def __bytes__(self, endianess: str = "big"):
        frame = bytearray(
            self.application_type.to_bytes(1, "big")
            + self.security_type.to_bytes(1, "big")
            + self.run_id
        )
        if endianess == "big":
            return frame
        return frame.reverse()

    def pack_big(self):
        return self.__bytes__()

    def pack_little(self):
        return self.__bytes__("little")

    @classmethod
    def from_bytes(cls, payload: ctypes) -> "SlacParmReq":
        return cls(
            application_type=payload[19],
            security_type=payload[20],
            run_id=payload[21:29],
        )


@dataclass
class SlacParmCnf:
    # pylint: disable=too-many-instance-attributes
    """
    Unicast Message
    EVSE -> PEV

    PEV-HLE broadcasts CM_SLAC_PARM requests until at least one
    matching CM_SLAC_PARM confirm is received; matching confirm
    has the same run identifier; EVSE-HLE returns information to
    the PEV-HLE;

    Associated with CM_SLAC_PARM.CNF, defined in chapter 11.5.46 of the HPGP
    standard. Check also table page 586, table 11-87

    Also table A.2 from ISO15118-3

    This payload is defined as follows, originally :
    | M-SOUND_TARGET | NUM_SOUNDS| Time_Out| RESP_TYPE |
    |FORWARDING_STA | APPLICATION_TYPE| SECURITY_TYPE| RunID| *CipherSuite*

    M-SOUND_TARGET [6 byte] - 0xFFFFFFFFFFFF: Indicates the MAC address of the
                                              GP STA with which the STA shall
                                              initiate the Signal Level
                                              Attenuation Characterization
                                              Process.Fixed value indicating
                                              that M-Sounds to be sent as
                                              Ethernet broadcast

    NUM_SOUNDS [1 byte] - SLAC_MSOUNDS: Number of expected M-Sounds
                                        transmitted by the GP station
                                        during the SLAC process
    Time_Out [1 byte] - SLAC_ATTEN_TIMEOUT: Duration TT_EVSE_match_MNBC while
                                          the EVSE receives incoming M-SOUNDS
                                          after a CM_START_ATTEN_CHAR.IND. On
                                          other words, indicates the amount of
                                          time within which the GP STA will
                                          complete the transmission of SOUND
                                          MPDUs during the Signal Level
                                          Attenuation Characterization Process.
                                          The time is in multiples of 100 msec.
                                          E.g, Time_Out = 6 corresponds to 600ms

    RESP_TYPE [1 byte] - SLAC_RESP_TYPE: Fixed value indicating 'Other GP station'
                                         Indicates whether the recipient of the
                                         SOUND MPDUs shall communicate the signal
                                         attenuation characteristic profile data to
                                         the HLE or another GP STA.
    FORWARDING_STA [6 bytes]: EV Host MAC; The destination of SLAC results is
                              always the EV Host. Only valid if RESP_TYPE = 0x01
    APPLICATION_TYPE [1 byte] - 0x00: Fixed value indicating 'PEV-EVSE Matching'
    SECURITY_TYPE [1 byte] - 0x00: Fixed value indicating “No Security”
    RunID [8 bytes]: This value shall be the same as the one sent in the
                     CM_SLAC_PARM.REQ message by the EV
    * CipherSuite [2 bytes] *: Selected Cipher Suite

    *Since Security Type is 0x00, CipherSuite wont be present in the payload

    Message size is = 25 bytes
    """
    # 6 bytes
    forwarding_sta: bytes
    # 8 bytes
    run_id: bytes
    msound_target: bytes = BROADCAST_ADDR
    num_sounds: int = SLAC_MSOUNDS
    time_out: int = SLAC_ATTEN_TIMEOUT
    resp_type: int = SLAC_RESP_TYPE
    application_type: int = SLAC_APPLICATION_TYPE
    security_type: int = SLAC_SECURITY_TYPE

    def __bytes__(self, endianess: str = "big"):
        frame = bytearray(
            self.msound_target
            + self.num_sounds.to_bytes(1, "big")
            + self.time_out.to_bytes(1, "big")
            + self.resp_type.to_bytes(1, "big")
            + self.forwarding_sta
            + self.application_type.to_bytes(1, "big")
            + self.security_type.to_bytes(1, "big")
            + self.run_id
        )
        if endianess == "big":
            return frame
        return frame.reverse()

    def pack_big(self):
        return self.__bytes__()

    def pack_little(self):
        return self.__bytes__("little")

    @classmethod
    def from_bytes(cls, payload: ctypes) -> "SlacParmCnf":

        return cls(
            msound_target=payload[19:25],
            num_sounds=payload[25],
            time_out=payload[26],
            resp_type=payload[27],
            forwarding_sta=payload[28:34],
            application_type=payload[34],
            security_type=payload[35],
            run_id=payload[36:44],
        )


@dataclass
class StartAtennChar:
    """
    Broadcast Message

    PEV -> EVSE

    Associated with CM_START_ATTEN_CHAR.IND in chapter 11.5.47 of the HPGP
    standard. Check also table page 586, table 11-87

    Also table A.4 from ISO15118-3

    This payload is defined as follows originally :

    |Application Type|Security Type| NUM_SOUNDS| Time_Out| RESP_TYPE |
    |FORWARDING_STA |RunID|


    Application Type [1 byte]: 0x00 Fixed value indicating 'PEV- EVSE matching'
    Security Type [1 bytes]: 0x00 Fixed value indicating 'No Security'

    The following parameters are under a nested field called in the HPGP
    standard as ACVarField (Attenuation Characterization Variable Field)

    NUM_SOUNDS [1 byte]: Number of M-Sounds transmitted by the GP station
                         during the SLAC process
    Time_Out [1 byte]: Max time window on which the M-Sounds are sent,
                       associated with TT_EVSE_match_MNBC of the spec and
                       SLAC_ATTEN_TIMEOUT of enums.py. Multiple of 100 ms, i.e.,
                       if Time_Out = 6, it means the timeout is equal to 600ms
    RESP_TYPE [1 byte] - SLAC_RESP_TYPE: Fixed value indicating
                                         'Other Green PHY station'
    FORWARDING_STA [6 bytes]: EV Host MAC; The destination of SLAC results is
                              always the EV Host
    RunID [8 bytes]: This value shall be the same as the one in
                     CM_SLAC_PARM.REQ message sent by the EV

    Message size is = 19 bytes
    """

    num_sounds: int
    time_out: int
    # 6 bytes
    forwarding_sta: bytes
    # 8 bytes
    run_id: bytes
    application_type: int = SLAC_APPLICATION_TYPE
    security_type: int = SLAC_SECURITY_TYPE
    resp_type: int = SLAC_RESP_TYPE

    def __bytes__(self, endianess: str = "big"):
        frame = bytearray(
            self.application_type.to_bytes(1, "big")
            + self.security_type.to_bytes(1, "big")
            + self.num_sounds.to_bytes(1, "big")
            + self.time_out.to_bytes(1, "big")
            + self.resp_type.to_bytes(1, "big")
            + self.forwarding_sta
            + self.run_id
        )
        if endianess == "big":
            return frame
        return frame.reverse()

    def pack_big(self):
        return self.__bytes__()

    def pack_little(self):
        return self.__bytes__("little")

    @classmethod
    def from_bytes(cls, payload: ctypes) -> "StartAtennChar":
        return cls(
            application_type=payload[19],
            security_type=payload[20],
            num_sounds=payload[21],
            time_out=payload[22],
            resp_type=payload[23],
            forwarding_sta=payload[24:30],
            run_id=payload[30:38],
        )


@dataclass
class MnbcSound:
    """
    Broadcast Message

    PEV -> EVSE (HPGP Node)

    Associated with CM_MNBC_SOUND.IND in chapter 11.5.54 of the HPGP
    standard. Check also table page 586, table 11-87

    Also table A.4 from ISO15118-3

    This payload is defined as follows, originally :

    |Application Type|Security Type|SenderID|Cnt|RunID|RSVD|Rnd|


    Application Type [1 byte]: 0x00 Fixed value indicating 'PEV- EVSE matching'
    Security Type [1 bytes]: 0x00 Fixed value indicating 'No Security'

    The following parameters are under a nested field called in the HPGP
    standard as MSVarField (MNBC Sound Variable Field)

    SenderID [17 bytes] - 0x00: Sender’s Identification. According to HPGP:
                                If APPLICATION_TYPE=0x00 then Sender ID is
                                PEV’s VIN code.
                                But 15118-3 defines it as 0x00
    Cnt [1 byte]: Countdown counter for number of Sounds remaining

    According to HPGP spec, RunID has 16 Bytes, but 15118-3 just uses 8 bytes,
    so the other 8 are set to 0x00 and are reserved

    RunID [8 bytes]: This value shall be the same as the one in
                     CM_SLAC_PARM.REQ message sent by the EV
    RSVD [8 bytes] - 0x00: Reserved
    Rnd [16 bytes]: Random Value

    Message size is = 52 bytes
    """

    cnt: int
    # 8 bytes
    run_id: bytes
    application_type: int = SLAC_APPLICATION_TYPE
    security_type: int = SLAC_SECURITY_TYPE
    # 17 bytes
    sender_id: int = 0x00
    # 8 bytes
    rsvd: int = 0x00
    # 16 bytes
    rnd: int = 0xFF01

    def __bytes__(self, endianess: str = "big"):
        frame = bytearray(
            self.application_type.to_bytes(1, "big")
            + self.security_type.to_bytes(1, "big")
            + self.sender_id.to_bytes(17, "big")
            + self.cnt.to_bytes(1, "big")
            + self.run_id
            + self.rsvd.to_bytes(8, "big")
            + self.rnd.to_bytes(16, "big")
        )
        if endianess == "big":
            return frame
        return frame.reverse()

    def pack_big(self):
        return self.__bytes__()

    def pack_little(self):
        return self.__bytes__("little")

    @classmethod
    def from_bytes(cls, payload: ctypes) -> "MnbcSound":
        return cls(
            application_type=payload[19],
            security_type=payload[20],
            sender_id=int.from_bytes(payload[21:38], "big"),
            cnt=payload[38],
            run_id=payload[39:47],
            rsvd=int.from_bytes(payload[47:55], "big"),
            rnd=int.from_bytes(payload[55:71], "big"),
        )


@dataclass
class AttenProfile:
    """
    Sent by the HLE (HighLevel Entity/PLC chip) to the EVSE host application

    Associated with CM_ATTEN_PROFILE.IND

    Check table A.4 from ISO15118-3

    This payload is defined as follows originally :

    |PEV MAC|NumGroups|RSVD|AAG 1| AAG 2| AAG 3...|


    PEV MAC [6 byte]: MAC address of EV Host
    NumGroups [1 bytes]: 0x3A Number of OFDM carrier groups used for the SLAC
                              signal characterization.
    RSVD [1 bytes] - 0x00: Reserved
    AAG 1 [1 byte]: Average Attenuation of Group 1
    AAG Nth [1 byte]: Average Attenuation of Group Nth

    Message size is = 66 bytes
    """

    pev_mac: bytes
    # it has the length of num_groups bytes
    aag: List[int]
    # 0x3A = 58 Groups
    num_groups: int = 0x3A
    rsvd: int = 0x00

    def __bytes__(self, endianess: str = "big"):
        # I probably could use here
        # ``` python
        # bytearray(self.aag)
        # ```
        # but I wouldnt have
        # control over the number of groups used, so I decided here to go safe
        aag_bytes = b""
        for group in range(self.num_groups):
            aag_bytes += self.aag[group].to_bytes(1, "big")
        frame = bytearray(
            self.pev_mac
            + self.num_groups.to_bytes(1, "big")
            + self.rsvd.to_bytes(1, "big")
            + aag_bytes
        )
        if endianess == "big":
            return frame
        return frame.reverse()

    def pack_big(self):
        return self.__bytes__()

    def pack_little(self):
        return self.__bytes__("little")

    @classmethod
    def from_bytes(cls, payload: ctypes) -> "AttenProfile":
        num_groups = payload[25]
        return cls(
            pev_mac=payload[19:25],
            num_groups=num_groups,
            rsvd=payload[26],
            aag=list(payload[27 : 27 + num_groups]),
        )


@dataclass
class AtennChar:
    # pylint: disable=too-many-instance-attributes
    """
    Unicast Message

    Associated with CM_ATTEN_CHAR.IND in chapter 11.5.48 of the HPGP
    standard. Check also table page 586, table 11-87

    With this message, the EVSE shares with the PEV, the results of
    the sounds received per group.

    Also table A.4 from ISO15118-3

    EVSE -> PEV

    This payload is defined as follows originally :

    |Application Type|Security Type| SOURCE_ADDRESS| RunID| SOURCE_ID| RESP_ID|
    |NumSounds| ATTEN_PROFILE|

    ATTEN_PROFILE = |NumGroups|AAG 1| AAG 2| AAG 3...|

    Application Type [1 byte]: 0x00 Fixed value indicating 'PEV- EVSE matching'
    Security Type [1 bytes]: 0x00 Fixed value indicating 'No Security'

    The following parameters are under a nested field called in the HPGP
    standard as ACVarField (Attenuation Characterization Variable Field)

    SOURCE_ADDRESS [6 bytes]: MAC Address of EV Host which initiated the SLAC
    RunID [8 bytes]: This value shall be the same as the one in
                     CM_SLAC_PARM.REQ message sent by the EV
    SOURCE_ID [17 bytes] - 0x00...00: - The unique identifier of the station
                                        that sent the M-Sounds (not used by ISO)
    RESP_ID [17 bytes] - 0x00...00: - The unique identifier of the station that
                                      is sending this message (not used by ISO)
    NUM_SOUNDS [1 byte]: Number of M-Sounds used for generation of the
                         ATTEN_PROFILE
    ATTEN_PROFILE [59 bytes]: Signal Level Attenuation (Field format in table
                              'ATTEN_PROFILE' of [HPGP])
                              ATTEN_PROFILE = |NumGroups|AAG 1| AAG 2| AAG 3...|

    Message size is = 110 bytes
    """
    # 6 bytes
    source_address: bytes
    # 8 bytes
    run_id: bytes
    num_sounds: int
    num_groups: int
    #  255 bytes
    aag: List[int]

    application_type: int = SLAC_APPLICATION_TYPE
    security_type: int = SLAC_SECURITY_TYPE
    #  17 Bytes
    source_id: int = 0x00
    # 17 bytes
    resp_id: int = 0x00

    def __bytes__(self, endianess: str = "big"):
        frame = bytearray(
            self.application_type.to_bytes(1, "big")
            + self.security_type.to_bytes(1, "big")
            + self.source_address
            + self.run_id
            + self.source_id.to_bytes(17, "big")
            + self.resp_id.to_bytes(17, "big")
            + self.num_sounds.to_bytes(1, "big")
            + self.num_groups.to_bytes(1, "big")
            + bytearray(self.aag)
        )
        if endianess == "big":
            return frame
        return frame.reverse()

    def pack_big(self):
        return self.__bytes__()

    def pack_little(self):
        return self.__bytes__("little")

    @classmethod
    def from_bytes(cls, payload: ctypes) -> "AtennChar":
        num_groups = payload[70]
        return cls(
            application_type=payload[19],
            security_type=payload[20],
            source_address=payload[21:27],
            run_id=payload[27:35],
            source_id=int.from_bytes(payload[35:52], "big"),
            resp_id=int.from_bytes(payload[52:69], "big"),
            num_sounds=payload[69],
            num_groups=num_groups,
            aag=list(payload[71 : 71 + num_groups]),
        )


@dataclass
class AtennCharRsp:
    """
    Unicast Message

    Associated with CM_ATTEN_CHAR.RSP in chapter 11.5.49 of the HPGP
    standard. Check also table page 586, table 11-87

    Also table A.4 from ISO15118-3

    PEV -> EVSE

    This payload is defined as follows originally :

    |Application Type|Security Type| SOURCE_ADDRESS| RunID| SOURCE_ID| RESP_ID|
    |Result|


    Application Type [1 byte]: 0x00 Fixed value indicating 'PEV- EVSE matching'
    Security Type [1 bytes]: 0x00 Fixed value indicating 'No Security'

    The following parameters are under a nested field called in the HPGP
    standard as ACVarField (Attenuation Characterization Variable Field)

    SOURCE_ADDRESS [6 bytes]: MAC Address of EV Host which initiated the SLAC
    RunID [8 bytes]: This value shall be the same as the one in
                     CM_SLAC_PARM.REQ message sent by the EV
    SOURCE_ID [17 bytes] - 0x00: - HPGP defines it as the unique identifier
                                 from the station that sent the M-sounds.
                                 ISO15118-3 defines it as 0x00
    RESP_ID [17 byte] - 0x00: - HPGP defines it as the unique identifier
                               of the station that is sending this message.
                               ISO15118-3 defines it as 0x00
    Result [1 byte] - 0x00: Fixed value of 0x00 indicates a successful SLAC
                            process

    Message size is = 43 bytes
    """

    # 6 bytes
    source_address: bytes
    # 8 bytes
    run_id: bytes
    #  17 Bytes
    source_id: int
    # 17 bytes
    resp_id: int
    #  1 byte
    result: int

    application_type: int = SLAC_APPLICATION_TYPE
    security_type: int = SLAC_SECURITY_TYPE

    def __bytes__(self, endianess: str = "big"):
        frame = bytearray(
            self.application_type.to_bytes(1, "big")
            + self.security_type.to_bytes(1, "big")
            + self.source_address
            + self.run_id
            + self.source_id.to_bytes(17, "big")
            + self.resp_id.to_bytes(17, "big")
            + self.result.to_bytes(1, "big")
        )
        if endianess == "big":
            return frame
        return frame.reverse()

    def pack_big(self):
        return self.__bytes__()

    def pack_little(self):
        return self.__bytes__("little")

    @classmethod
    def from_bytes(cls, payload: ctypes) -> "AtennCharRsp":
        return cls(
            application_type=payload[19],
            security_type=payload[20],
            source_address=payload[21:27],
            run_id=payload[27:35],
            source_id=int.from_bytes(payload[35:52], "big"),
            resp_id=int.from_bytes(payload[52:69], "big"),
            result=payload[69],
        )


@dataclass
class MatchReq:
    # pylint: disable=too-many-instance-attributes
    """
    Unicast Message

    Associated with CM_SLAC_MATCH.REQ in chapter 11.5.57 of the HPGP
    standard. Check also table A.7 from ISO15118-3

    PEV -> EVSE

    This payload is defined as follows originally :

    |Application Type|Security Type| MVFLength| PEV_ID| PEV_MAC| EVSE_ID|
    EVSE MAC|RunID|RSVD|


    Application Type [1 byte] - 0x00: Fixed value indicating 'PEV- EVSE matching'
    Security Type [1 bytes] - 0x00: Fixed value indicating 'No Security'
    MVFLength [2 bytes] - 0x3e: (Fixed value) Match Variable Field Length

    The following parameters are under a nested field called in the HPGP
    standard as MatchVarField (Match Variable Field)

    PEV ID [17 bytes] - 0x00:
    PEV MAC [6 bytes]: MAC Address of the EV Host
    EVSE ID [17 bytes] - 0x00:
    EVSE MAC [6 bytes]: MAC Address of the EVSE Host
    RunID [8 bytes]: This value shall be the same as the one in
                     CM_SLAC_PARM.REQ message sent by the EV
    RSVD [8 bytes] - 0x00: Reserved

    Message size is = 62 bytes
    """
    # 6 bytes
    pev_mac: bytes
    # 6 bytes
    evse_mac: bytes
    # 8 bytes
    run_id: bytes
    application_type: int = SLAC_APPLICATION_TYPE
    security_type: int = SLAC_SECURITY_TYPE
    # 2 bytes
    mvf_length: int = 0x003E
    # 17 bytes
    pev_id: int = 0x00
    # 17 bytes
    evse_id: int = 0x00
    # 8 bytes
    rsvd: int = 0x00

    def __bytes__(self, endianess: str = "big"):
        frame = bytearray(
            self.application_type.to_bytes(1, "big")
            + self.security_type.to_bytes(1, "big")
            + self.mvf_length.to_bytes(2, "big")
            + self.pev_id.to_bytes(17, "big")
            + self.pev_mac
            + self.evse_id.to_bytes(17, "big")
            + self.evse_mac
            + self.run_id
            + self.rsvd.to_bytes(8, "big")
        )
        if endianess == "big":
            return frame
        return frame.reverse()

    def pack_big(self):
        return self.__bytes__()

    def pack_little(self):
        return self.__bytes__("little")

    @classmethod
    def from_bytes(cls, payload: ctypes) -> "MatchReq":
        return cls(
            application_type=payload[19],
            security_type=payload[20],
            mvf_length=int.from_bytes(payload[21:23], "big"),
            pev_id=int.from_bytes(payload[23:40], "big"),
            pev_mac=payload[40:46],
            evse_id=int.from_bytes(payload[46:63], "big"),
            evse_mac=payload[63:69],
            run_id=payload[69:77],
            rsvd=int.from_bytes(payload[77:85], "big"),
        )


@dataclass
class MatchCnf:
    # pylint: disable=too-many-instance-attributes
    """
    Unicast Message

    Associated with CM_SLAC_MATCH.CNF in chapter 11.5.58 of the HPGP
    standard. Check also table A.7 from ISO15118-3

    The selected EVSE responses to the EV request with a CM_SLAC_MATCH.CNF,
    which contains all parameters to be set to join the logical network of
    the EVSE.

    EVSE -> PEV

    This payload is defined as follows originally:

    |Application Type|Security Type| MVFLength| PEV_ID| PEV_MAC| EVSE_ID|
    EVSE MAC|RunID|RSVD1|NID|RSVD2|NMK


    Application Type [1 byte] - 0x00: Fixed value indicating 'PEV- EVSE matching'
    Security Type [1 bytes] - 0x00: Fixed value indicating 'No Security'
    MVFLength [2 bytes] - 0x56: (Fixed value) Match Variable Field Length

    The following parameters are under a nested field called in the HPGP
    standard as MatchVarField (Match Variable Field)

    PEV ID [17 bytes] - 0x00:
    PEV MAC [6 bytes]: MAC Address of the EV Host
    EVSE ID [17 bytes] - 0x00:
    EVSE MAC [6 bytes]: MAC Address of the EVSE Host
    RunID [8 bytes]: This value shall be the same as the one in
                     CM_SLAC_PARM.REQ message sent by the EV
    RSVD1 [8 bytes] - 0x00: Reserved
    NID [7 bytes]: Network ID derived from the NMK by the EVSE
                   according to [HPGP], 4.4.3.1
    RSVD2 [8 bytes] - 0x00: Reserved
    NMK [16 bytes]: Private Network Membership Key of the EVSE (random value)

    Message size is = 97 bytes
    """
    # 6 bytes
    pev_mac: bytes
    # 6 bytes
    evse_mac: bytes
    # 8 bytes
    run_id: bytes
    # 7 bytes
    nid: bytes
    # 16 bytes
    nmk: bytes
    application_type: int = SLAC_APPLICATION_TYPE
    security_type: int = SLAC_SECURITY_TYPE
    # 2 bytes
    mvf_length: int = 0x56
    # 17 bytes
    pev_id: int = 0x00
    # 17 bytes
    evse_id: int = 0x00
    # 8 bytes
    rsvd_1: int = 0x00
    # 1 bytes
    rsvd_2: int = 0x00

    def __bytes__(self, endianess: str = "big"):
        frame = bytearray(
            self.application_type.to_bytes(1, "big")
            + self.security_type.to_bytes(1, "big")
            + self.mvf_length.to_bytes(2, "little")  # MVF is sent in little endian
            + self.pev_id.to_bytes(17, "big")
            + self.pev_mac
            + self.evse_id.to_bytes(17, "big")
            + self.evse_mac
            + self.run_id
            + self.rsvd_1.to_bytes(8, "big")
            + self.nid
            + self.rsvd_2.to_bytes(1, "big")
            + self.nmk
        )
        if endianess == "big":
            return frame
        return frame.reverse()

    def pack_big(self):
        return self.__bytes__()

    def pack_little(self):
        return self.__bytes__("little")

    @classmethod
    def from_bytes(cls, payload: ctypes) -> "MatchCnf":
        return cls(
            application_type=payload[19],
            security_type=payload[20],
            mvf_length=int.from_bytes(payload[21:23], "big"),
            pev_id=int.from_bytes(payload[23:40], "big"),
            pev_mac=payload[40:46],
            evse_id=int.from_bytes(payload[46:63], "big"),
            evse_mac=payload[63:69],
            run_id=payload[69:77],
            rsvd_1=int.from_bytes(payload[77:85], "big"),
            nid=payload[85:92],
            rsvd_2=payload[92],
            nmk=payload[93:109],
        )
