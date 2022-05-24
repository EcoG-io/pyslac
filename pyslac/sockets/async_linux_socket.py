import asyncio
import logging
from ctypes import addressof, create_string_buffer

# pylint: disable=no-name-in-module
from socket import (
    AF_PACKET,
    SO_BROADCAST,
    SOCK_RAW,
    SOL_SOCKET,
    gethostbyname,
    gethostname,
    htons,
    socket,
)
from struct import pack
from typing import Optional

from pyslac.enums import BUFF_MAX_SIZE, Timers
from pyslac.sockets.enums import (
    BPF_ABS,
    BPF_H,
    BPF_JEQ,
    BPF_JMP,
    BPF_K,
    BPF_LD,
    BPF_RET,
    ETH_P_ALL,
    ETH_P_HPAV,
    SO_ATTACH_FILTER,
)
from pyslac.utils import time_now_ms

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("async_linux_socket")


def bpf_jump(code, k, jt, jf):
    return pack("HBBI", code, jt, jf, k)


def bpf_stmt(code, k):
    return bpf_jump(code, k, 0, 0)


# Ordering of the filters is backwards of what would be intuitive for
# performance reasons: the check that is most likely to fail is first.
# A BPF filter code works a bit as assembly code where we have instructions and
# we can jump over them and can load memory positions. The anatomy of a jump
# instruction is as follows:
# bpf_jump(BPF_JMP | BPF_JEQ | BPF_K, <val>, <jtrue>, <jfalse>)
# which basically says, if the value in register BPF_K is equal to <val>,
# then jump <jtrue> instructuins, otherwise jump <jfalse> instructions.
# bpf_stmt(BPF_LD | BPF_H | BPF_ABS, <mem position/ byte offset>)
# this instruction loads to the memory the data present in the register defined
# by the <offset>
# The instruction says Load (BPF_LD) a half word value (BPF_H) in
# from a absolute byte offset (BPF_ABS), in our case, below, that offset is 12.
# An example can be found in
# http://allanrbo.blogspot.com/2011/12/raw-sockets-with-bpf-in-python.html
filters_list = [
    # In this case we want to filter out all ethernet frames whose Ether type
    # is NOT ETH_P_HPAV. Since MAC Dest and Mac source each have 6 bytes,
    # our 2-Octet Ether type is found starting in mem position 12
    # Must be HPGP (check ethertype field at byte offset 12)
    bpf_stmt(BPF_LD | BPF_H | BPF_ABS, 12),
    # If the Ether Type is ETH_P_HPAV, we dont jump and the instruction
    # bpf_stmt(BPF_RET | BPF_K, 0x0fffffff) is run and returns success (-1)
    # otherwise, we jump and we run bpf_stmt(BPF_RET | BPF_K, 0)
    # returning failure (0)
    bpf_jump(BPF_JMP | BPF_JEQ | BPF_K, ETH_P_HPAV, 0, 1),
    bpf_stmt(BPF_RET | BPF_K, 0x0FFFFFFF),  # pass returns -1 in bytes format
    bpf_stmt(BPF_RET | BPF_K, 0),  # reject
]


# TODO:
# Create the socket outside and inject it here
# maybe even create a receive routine inside a task that then sends the
# the frames received using a channel or something


def create_socket(iface: str, port=0) -> socket:
    """
    Creates and binds the raw socket to the desired interface combined with a
    BPF filter

    """
    # Create filters struct and fprog struct to be used by SO_ATTACH_FILTER, as
    # defined in linux/filter.h.
    # An example can be found in
    # http://allanrbo.blogspot.com/2011/12/raw-sockets-with-bpf-in-python.html
    filters = b"".join(filters_list)
    b = create_string_buffer(filters)
    mem_addr_of_filters = addressof(b)
    fprog = pack("HL", len(filters_list), mem_addr_of_filters)

    # https://github.com/spotify/linux/blob/master/include/linux/if_ether.h
    # The link above defines the different protocol (proto) packets that the
    # socket shall receive. By default is 0 (socket.IPPROTO_IP).
    # But we want to receive something, so we use ETH_P_ALL = 0x0003
    # which means receive every packet! (we may want to specify it better
    # the kind)

    # Defining the socket Protocol as ETH_P_ALL, forces the socket to
    # accept all packages during reception (readeth)
    s = socket(AF_PACKET, SOCK_RAW, htons(ETH_P_ALL))
    s.setsockopt(SOL_SOCKET, SO_ATTACH_FILTER, fprog)
    # This option ususally sets up the socket to accept Broadcast messages
    # but I tested without and also works. Nevertheless, let's keep it...
    s.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
    # The documentation specifies that for the use of the loop socket
    # API, the socket must be non blocking
    # https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.loop.sock_recv
    s.setblocking(False)

    # From the docs: "For raw packet
    # sockets the address is a tuple (ifname, proto [,pkttype [,hatype]])"
    s.bind((iface, port))

    return s


async def sendeth(
    frame_to_send: bytes, iface: Optional[str] = None, port: int = 0, s: socket = None
):
    """Send raw Ethernet packet on interface."""
    loop = asyncio.get_event_loop()

    if not iface:
        iface = gethostbyname(gethostname())

    if not s or not isinstance(s, socket):
        s = create_socket(iface, port)

    padding_bytes = b"\x00" * (60 - len(frame_to_send))
    frame_to_send = frame_to_send + padding_bytes

    return await loop.sock_sendall(s, frame_to_send)


async def readeth_into(s: socket, _):
    """
    https://docs.python.org/3.8/library/asyncio-eventloop.html#asyncio.loop.sock_recv_into

    This alternative requires more testing
    """
    loop = asyncio.get_event_loop()
    data = bytearray(100)
    bytes_rcvd = await loop.sock_recv_into(s, data)
    return data, bytes_rcvd


async def readeth(
    s: socket = None,
    iface: str = None,
    port: int = 0,
    rcv_frame_size: int = BUFF_MAX_SIZE,
    time_start: int = time_now_ms(),
) -> bytes:

    loop = asyncio.get_event_loop()

    if not iface:
        iface = gethostbyname(gethostname())

    if not s or not isinstance(s, socket):
        s = create_socket(iface, port)

    # Maybe I will have to check if the src MAC corresponds to the dst MAC from
    # the sending packet
    bytes_rcvd = await loop.sock_recv(s, rcv_frame_size)
    # NOTE: awaiting for the exact number of bytes expected will just be done,
    # if the rcv frame size is a number below the max ETH PDU possible
    bytes_left = rcv_frame_size - len(bytes_rcvd)
    if bytes_left > 0 and rcv_frame_size < BUFF_MAX_SIZE:
        time_elapsed = time_now_ms() - time_start
        if time_elapsed > Timers.SLAC_INIT_TIMEOUT * 1000:  # in ms
            raise asyncio.TimeoutError
        bytes_rcvd = bytes_rcvd + await readeth(s=s, iface=iface, time_start=time_start)
    return bytes_rcvd


async def send_recv_eth(
    frame_to_send: bytes,
    s: socket = None,
    iface: str = None,
    rcv_frame_size: int = BUFF_MAX_SIZE,
):
    # pylint: disable=lost-exception
    data_rcvd = None
    port = 0

    if not iface:
        iface = gethostbyname(gethostname())

    if not s or not isinstance(s, socket):
        s = create_socket(iface, port)

    try:
        padding_bytes = b"\x00" * (60 - len(frame_to_send))
        frame_to_send = frame_to_send + padding_bytes
        await sendeth(frame_to_send, s=s)
        data_rcvd = await asyncio.wait_for(
            readeth(s=s, iface=iface, rcv_frame_size=rcv_frame_size),
            timeout=Timers.SLAC_INIT_TIMEOUT,
        )
    except asyncio.TimeoutError as e:
        logger.exception(e, exc_info=True)
        s.close()
        logger.info("Linux Socket closed")
        raise e
    finally:
        return data_rcvd
