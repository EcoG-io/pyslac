import asyncio
import logging
import socket
import struct
import time
from fcntl import ioctl
from hashlib import sha256
from math import copysign
from sys import platform
from typing import Any, Awaitable, List

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("slac_utils")

# commands
SIOCGIFHWADDR = 0x8927  # Get hardware address
SIOCGIFADDR = 0x8915  # get PA address

# From net/if_arp.h
ARPHDR_ETHER = 1
ARPHDR_METRICOM = 23
ARPHDR_PPP = 512
ARPHDR_LOOPBACK = 772
ARPHDR_TUN = 65534

NID_LENGTH = 7


def generate_nid(nmk: bytes):
    """
    It generates a NID key, based on the NMK, which is a random 16 bytes value.
    The way the NID is generated is by hashing recursively the NMK 5 times,
    reinitializing the sha256 buffer each time. It then collects the first
    7 bytes of the result and shifts 4 times the least significant byte.
    This algorithm was extracted from the Qualcomm implementation of it
    in https://github.com/qca/open-plc-utils/blob/master/key/HPAVKeyNID.c

    The procedure to get the NID described in the HPGP 1.1, section 4.4.3.1
    does not match the algorithm presented here and in fact makes no sense;
    During the testival in Stuttgart between 28-30 September 2021, tried to get
    someone to explain the logic described in HPGP but no one could.
    :param nmk: NMK [16 bytes] randomly generated
    :return: NID [7 bytes]
    """
    # For the sake of clarity, the attribute for the method is nmk, but over
    # the loop we want to keep updating the same variable and it becomes a
    # digest, so we set the initial digest variable value as equal to nmk
    digest = nmk
    for _ in range(5):
        _sha256 = sha256()
        _sha256.update(digest)
        digest = _sha256.digest()
    truncated_digest = digest[:NID_LENGTH]
    last_byte = NID_LENGTH - 1
    nid = truncated_digest[:last_byte] + (truncated_digest[last_byte] >> 4).to_bytes(
        1, "big"
    )
    return nid


def half_round(x):
    """
    Python round() function rounds the float number to the nearest even number,
    i.e:
    >> round(2.3)
       2
    >> round(2.5)
       2

    This happens because python 3.x in contrast to 2.x, uses Banker's rounding
    for the function (http://en.wikipedia.org/wiki/Banker's_rounding;
    https://wiki.c2.com/?BankersRounding)

    This function implements a half-way rounding, which is more commonly used,
    for positive and negative numbers. The copysign(0.5, x) provides the sign
    of the float number to be rounded and injects it in 0.5.

    """
    return int(x + copysign(0.5, x))


def time_now_ms():
    return round(time.time() * 1000)


def is_distro_linux() -> bool:
    """
    Checks if the Machine is a Linux one
    :return:
    """
    if platform.startswith("linux"):
        return True
    return False


def plain_str(x):
    """Convert basic byte objects to str"""
    if isinstance(x, bytes):
        return x.decode(errors="backslashreplace")
    return str(x)


def str2mac(s):
    """
    Returns the Mac Address in the format 00:00:00:00:00:00
    """
    if isinstance(s, str):
        return ("%02x:" * 6)[:-1] % tuple(map(ord, s))
    return ("%02x:" * 6)[:-1] % tuple(s)


def get_if_hwaddr(iff: str, to_mac_fmt=False):
    """
    Returns the MAC (hardware) address of an interface in readable format
    iff: interface name, e.g. en0 or enp0s3
    """

    addr_family, mac = get_if_raw_hwaddr_linux(iff)  # type: ignore # noqa: F405

    if addr_family in [ARPHDR_ETHER, ARPHDR_LOOPBACK]:
        if to_mac_fmt:
            return str2mac(mac)
        return mac
    raise Exception(
        f"Unsupported address family ({addr_family}) " "for interface [{iff}]"
    )


def get_if_raw_hwaddr_linux(iff: str, siocgifhwaddr: int = SIOCGIFHWADDR):
    """Get the raw MAC address of a local interface.
    This function uses SIOCGIFHWADDR (System I/O Command Get Interface HW Addr)
    calls, therefore only works
    on some distros.

    iff: str - Interface Designation (e.g. 'en0')
    siocgifhwaddr: int = SIOCGIFHWADDR - SIO command
    """

    sck = socket.socket()
    try:
        # input/output control
        raw_addr = ioctl(sck, siocgifhwaddr, struct.pack("16s16x", iff.encode("utf8")))
    except OSError as e:
        raise OSError(f"There is no such interface {iff}") from e
    finally:
        sck.close()
    # raw_addr is a 32 bytes buffer
    # 16 bytes are padding ones, thus they are ignored (16x)
    # we expect a short (h) - 2 bytes
    # a 6-bytes value that is converted as string (6s), like b'\x00\x01..\x06'
    # and 8 bytes are ignored as padding (8x)
    # so the value returned is a tuple with two items, like:
    # (1, b'\x02B\xac\x14\x00\x02')
    return struct.unpack("16xh6s8x", raw_addr)


async def cancel_task(task):
    """Cancel the task safely"""
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


def task_callback(task: asyncio.Task):
    """
    Callback for a task
    This is very useful when spawning tasks in the background with asyncio.create_task.
    As the task runs in the background any runtime exception is not logged, so with this
    callback, it is possible to keep logging the exceptions
    https://stackoverflow.com/questions/66293545/asyncio-re-raise-exception-from-a-task
    """
    try:
        task.result()
    except asyncio.CancelledError:
        pass  # Task cancellation should not be logged as an error.
    except Exception as e:
        logger.error(f"Exception raised by task: {task.get_name()}", e)


async def wait_till_finished(
    awaitables: List[Awaitable[Any]], finished_when=asyncio.FIRST_EXCEPTION
):
    # pylint: disable=broad-except
    """Run the tasks until one task is finished. The condition to finish
    depends on the argument 'finished_when', which directly translates
    to the asyncio.wait argument 'return_when' that can assume the following
    values: FIRST_COMPLETED, FIRST_EXCEPTION, ALL_COMPLETED
    (For more information regarding this, please check:
    https://docs.python.org/3/library/asyncio-task.html#waiting-primitives)

    All unfinished tasks will be cancelled.

    It can happen that multiple tasks finished at the same time.
    A MultiError is raised if at least one task finished with an exception.
    This exception wraps the exception of all tasks that finished with an
    exception.

    Return values of finished tasks are ignored. Use `asyncio.wait()` directly
    if you need access to the return values of tasks.

    If this function turns out to be useful it might be a good fit for
    `common/util` or `cc_utils`.

    """
    tasks = []

    # As of Python 3.8 `asyncio.wait()` should be called only with
    # `asyncio.Task`s.
    # See: https://docs.python.org/3/library/asyncio-task.html#asyncio-example-wait-coroutine  # noqa: E501
    for awaitable in awaitables:
        if not isinstance(awaitable, asyncio.Task):
            awaitable = asyncio.create_task(awaitable)
        tasks.append(awaitable)

    done, pending = await asyncio.wait(tasks, return_when=finished_when)

    for task in pending:
        await cancel_task(task)

    errors = []
    for task in done:
        try:
            task.result()
        except Exception as ex:
            logger.exception(ex)
            errors.append(ex)

    if len(errors) == 1:
        raise errors[0]

    if errors:
        raise MultiError(errors)


class MultiError(Exception):
    """Exception used to raise multiple exceptions.

    The attribute `errors` gives access to the wrapper errors.

        try:
            something()
        except MultiError as e:
            for error in e.errors:
                if isinstance(e, ZeroDivisionError):
                    ...
                elif isinstance(e, AttributeError):
                    ...

    """

    def __init__(self, errors: List[Exception]):
        Exception.__init__(self)
        self.errors = errors
