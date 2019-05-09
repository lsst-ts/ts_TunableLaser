from lsst.ts.laser import AsciiSerial
from unittest.mock import Mock
import pytest

class TestAsciiSerial:
    @pytest.fixture(scope="class")
    def serial(self):
        serial = AsciiSerial(None)
        return serial

    def test_parse_reply(self,serial):
        reply = "525nm\r\x03".encode('ascii')
        response = serial.parse_reply(reply)
        assert response == "525"


class TestAsciiRegister:
    @pytest.fixture(scope="class")
    def register(self):
        pass
