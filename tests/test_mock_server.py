import unittest

from lsst.ts.tunablelaser.mock_server import MockMessage, MockNT900


class TestMockMessage(unittest.TestCase):
    def test_bad_message(self):
        with self.assertRaises(Exception):
            MockMessage(b"xdfgghtb")


class TestMockNT900(unittest.TestCase):
    def test_check_limits(self):
        device = MockNT900()
        reply = device.check_limits(200, 300, 1100)
        assert reply == "'''Error: (12) Violating bottom value limit\r\n\x03"
        reply = device.check_limits(1200, 300, 1100)
        assert reply == "'''Error: (11) Violating top value limit\r\n\x03"

    def test_do_change_continuous_burst_mode_trigger_burst(self):
        device = MockNT900()
        reply = device.do_set_m_cpu800_18_continuous_burst_mode_trigger_burst("wumbo")
        assert (
            reply
            == "'''Error: (13) Wrong value, not included in allowed values list\r\n\x03"
        )
