from unittest.mock import Mock, patch

import pytest

from slac.session import SlacEvseSession


@pytest.fixture
def dummy_iface():
    return "en0"


@pytest.fixture
def evse_mac():
    return b"\xAB" * 6


@pytest.fixture
def evse_slac_session(dummy_iface, evse_mac):
    with patch("slac.session.get_if_hwaddr", new=Mock(return_value=evse_mac)):
        with patch("slac.session.create_socket", new=Mock()):
            evse_session = SlacEvseSession(dummy_iface)
            evse_session.reset_socket = Mock()

    return evse_session
