from dataclasses import dataclass

from pyslac.enums import ETH_TYPE_HPAV, HOMEPLUG_FMID, HOMEPLUG_FMSN, HOMEPLUG_MMV


@dataclass
class EthernetHeader:
    #  6 bytes (channel peer)
    dst_mac: bytes
    #  6 bytes (channel host)
    src_mac: bytes
    #  2 bytes (channel type)
    ether_type: int = ETH_TYPE_HPAV

    def __bytes__(self, endianess: str = "big"):
        if endianess == "big":
            return self.dst_mac + self.src_mac + self.ether_type.to_bytes(2, "big")
        return (
            self.ether_type.to_bytes(2, "little")
            + (int.from_bytes(self.src_mac, "big")).to_bytes(6, "little")
            + (int.from_bytes(self.dst_mac, "big")).to_bytes(6, "little")
        )

    def pack_big(self):
        return self.__bytes__()

    def pack_little(self):
        return self.__bytes__("little")

    @classmethod
    def from_bytes(cls, payload: bytes):
        return cls(
            dst_mac=payload[:6],
            src_mac=payload[6:12],
            ether_type=int.from_bytes(payload[12:14], "big"),
        )


@dataclass
class HomePlugHeader:
    """
    All messages defined in HomePlug GREEN PHY specification Version 1.0 shall
    have the MMV field set to 0x01. HPGP spec page 494

    This payload is defined as follows:
    | MMV | MMTYPE | FMSN | FMID |

    MMV [1 byte] = 0x01
    MMTYPE [2 bytes]: Or operation between the MMID (called MM Base value)
                      to be sent and the mm_type (REQ or CNF)
                      The Management Message Ids can be found in table 11-5
                      page 501 of HPGP standard
    FMSN [1 byte] - Fragmentation Message Sequence number = 0x00
    FMID [1 byte] = 0x00
    """

    mm_type: int
    mmv: bytes = HOMEPLUG_MMV
    fmsn: bytes = HOMEPLUG_FMSN
    fmid: bytes = HOMEPLUG_FMID

    def __bytes__(self, endianess: str = "big"):
        if endianess == "big":
            # The MMType is sent in little endian format
            return self.mmv + self.mm_type.to_bytes(2, "little") + self.fmsn + self.fmid
        return self.fmid + self.fmsn + self.mm_type.to_bytes(2, "little") + self.mmv

    def pack_big(self):
        return self.__bytes__()

    def pack_little(self):
        return self.__bytes__("little")

    @classmethod
    def from_bytes(cls, payload: bytes):
        return cls(
            mmv=payload[14].to_bytes(1, "big"),
            mm_type=int.from_bytes(payload[15:17], "little"),
            fmsn=payload[17].to_bytes(1, "big"),
            fmid=payload[18].to_bytes(1, "big"),
        )
