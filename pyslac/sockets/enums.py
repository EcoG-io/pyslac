"""
from https://github.com/spotify/linux/blob/master/include/linux/if_ether.h
"""
import ctypes

#  BPF FILTERS ENUMS
# Instruction classes
BPF_LD = 0x00
BPF_JMP = 0x05
BPF_RET = 0x06

# ld/ldx fields
BPF_H = 0x08
BPF_B = 0x10
BPF_ABS = 0x20

# alu/jmp fields
BPF_JEQ = 0x10
BPF_K = 0x00

# As defined in asm/socket.h
SO_ATTACH_FILTER = 26


# ETH TYPE ENUMS
# Dummy type for 802.3 frames
ETH_P_802_3 = 0x0001
# Dummy protocol id for AX.25
ETH_P_AX25 = 0x0002
# Every packet (be careful!!!)
ETH_P_ALL = 0x0003
# Internet Protocol Packet
ETH_P_IP = 0x0800
# HomePlug AV Protocol Packet
ETH_P_HPAV = 0x88E1


# Used to set Promiscuous mode in Linux
# https://stackoverflow.com/questions/6067405/python-sockets-enabling-promiscuous-mode-in-linux/6072625
IFF_PROMISC = 0x100
SIOCGIFFLAGS = 0x8913
SIOCSIFFLAGS = 0x8914


class ifreq(ctypes.Structure):
    _fields_ = [("ifr_ifrn", ctypes.c_char * 16), ("ifr_flags", ctypes.c_short)]
