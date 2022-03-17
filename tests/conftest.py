from unittest.mock import Mock, patch

import pytest

from slac.environment import Config
from slac.session import SlacEvseSession

EVSE_ID = "DE*12*122333"
IFACE = "en0"


@pytest.fixture
def dummy_config() -> "Config":
    return Config(slac_init_timeout=1)


@pytest.fixture
def evse_mac():
    return b"\xAB" * 6


@pytest.fixture
def evse_slac_session(dummy_config, evse_mac):
    with patch("slac.session.get_if_hwaddr", new=Mock(return_value=evse_mac)):
        with patch("slac.session.create_socket", new=Mock()):
            evse_session = SlacEvseSession(EVSE_ID, IFACE, dummy_config)
            evse_session.reset_socket = Mock()

    return evse_session
