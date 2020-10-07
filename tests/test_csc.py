import unittest

from lsst.ts import salobj, tunablelaser
import asynctest


class TunableLaserCscTestCase(asynctest.TestCase, salobj.BaseCscTestCase):
    def basic_make_csc(self, initial_state, simulation_mode, config_dir):
        return tunablelaser.LaserCsc(
            initial_state=initial_state,
            simulation_mode=simulation_mode,
            config_dir=config_dir,
        )

    async def test_check_bin_script(self):
        await self.check_bin_script(
            name="TunableLaser", exe_name="run_tunable_laser.py", index=None
        )


if __name__ == "__main__":
    unittest.main()
