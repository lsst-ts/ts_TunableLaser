from lsst.ts.laser import LaserCSC
from lsst.ts import salobj
import pytest
class TestCsc:
    @pytest.fixture()
    def csc(self):
        csc = LaserCSC()
        return csc

    def test_csc(self, csc):
        pass
