from lsst.ts.laser.component import LaserComponent
import pytest
import subprocess

class TestLaserComponent:
    @pytest.fixture(scope="class")
    def socat(self):
        subprocess.Popen(["socat","-u", "-u", "pty,raw,echo=1,b19200", "pty,raw,echo=1,link=/tmp/ttyUSBLaser,user=ecoughlin"])

    @pytest.fixture(scope="class")
    def lc(self, socat):
        lc = LaserComponent("/tmp/ttyUSBLaser")
        return lc

    def test_check_errors(self, lc):
        with pytest.raises(Exception):
            reply = b"``` (-1) "
            lc._check_errors(reply)

