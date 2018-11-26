from lsst.ts.laser.component import LaserComponent
from serial import serial_for_url
from unittest.mock import Mock
import pytest

class TestLaserComponent:
    @pytest.fixture(scope="class")
    def lc(self):
        lc = LaserComponent(None)
        lc.serial = Mock()
        return lc

    @pytest.mark.parametrize('module',
                             ['CPU8000','M_CPU800','llPMKu','MaxiOPG','TK6','HV40W','DelayLin','MiniOPG','LDCO48BP',
                              'M_LDCO48'])
    def test_module_setup(self,lc,module):
        assert hasattr(lc,module)

    def test_parse_reply(self,lc):
        reply = lc._parse_reply(b"525nm\r\n\x03")
        assert reply == "525nm"

    def test_check_errors(self,lc):
        with pytest.raises(Exception):
            lc._check_errors("```\r\n")
        reply = lc._check_errors(b"\r\n")
        assert reply == b"\r\n"

    def test_read_module_register(self,lc,mocker):
        mocker.patch.object(lc.serial,'read_until',return_value=b"525nm\r\n\x03")
        mocker.patch.object(lc, '_check_errors', return_value=b"525nm\r\n\x03")
        mocker.patch.object(lc, '_parse_reply', return_value="525nm")
        lc._read_module_register(lc.MaxiOPG.name, lc.MaxiOPG.id, "WaveLength")
        assert lc.MaxiOPG.wavelength == "525nm"
