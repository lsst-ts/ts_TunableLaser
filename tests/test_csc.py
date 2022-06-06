# This file is part of ts_tunablelaser.
#
# Developed for the Vera Rubin Observatory Telescope and Site Software.
# This product includes software developed by the LSST Project
# (https://www.lsst.org).
# See the COPYRIGHT file at the top-level directory of this distribution
# for details of code ownership.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import unittest
import os
import pathlib

from lsst.ts import salobj, tunablelaser
from lsst.ts.idl.enums import TunableLaser


STD_TIMEOUT = 10
TEST_CONFIG_DIR = pathlib.Path(__file__).parents[1].joinpath("tests", "data", "config")


class TunableLaserCscTestCase(unittest.IsolatedAsyncioTestCase, salobj.BaseCscTestCase):
    def setUp(self) -> None:
        os.environ["LSST_SITE"] = "tunablelaser"
        return super().setUp()

    def basic_make_csc(self, initial_state, simulation_mode, config_dir):
        return tunablelaser.LaserCSC(
            initial_state=initial_state,
            simulation_mode=simulation_mode,
            config_dir=TEST_CONFIG_DIR,
        )

    async def test_check_bin_script(self):
        await self.check_bin_script(
            name="TunableLaser", exe_name="run_tunablelaser", index=None
        )

    async def test_standard_state_transitions(self):
        async with self.make_csc(initial_state=salobj.State.STANDBY, simulation_mode=1):
            await self.check_standard_state_transitions(
                enabled_commands=[
                    "changeWavelength",
                    "startPropagateLaser",
                    "stopPropagateLaser",
                    "clearLaserFault",
                ]
            )

    async def test_telemetry(self):
        async with self.make_csc(initial_state=salobj.State.ENABLED, simulation_mode=1):
            await self.assert_next_sample(
                topic=self.remote.tel_wavelength, wavelength=650
            )
            await self.assert_next_sample(
                topic=self.remote.tel_temperature,
                tk6_temperature=19,
                tk6_temperature_2=19,
                ldco48bp_temperature=19,
                ldco48bp_temperature_2=19,
                ldco48bp_temperature_3=19,
                m_ldco48_temperature=19,
                m_ldco48_temperature_2=19,
            )

    async def test_change_wavelength(self):
        async with self.make_csc(initial_state=salobj.State.ENABLED, simulation_mode=1):
            await self.remote.cmd_changeWavelength.set_start(
                wavelength=700, timeout=STD_TIMEOUT
            )
            await self.assert_next_sample(
                topic=self.remote.tel_wavelength, wavelength=700, flush=True
            )

    async def test_start_propagate_laser(self):
        async with self.make_csc(initial_state=salobj.State.ENABLED, simulation_mode=1):
            await self.assert_next_sample(
                topic=self.remote.evt_detailedState,
                detailedState=TunableLaser.LaserDetailedState.NONPROPAGATING,
            )
            await self.remote.cmd_startPropagateLaser.set_start(timeout=STD_TIMEOUT)
            await self.assert_next_sample(
                topic=self.remote.evt_detailedState,
                detailedState=TunableLaser.LaserDetailedState.PROPAGATING,
            )

    async def test_stop_propagate_laser(self):
        async with self.make_csc(initial_state=salobj.State.ENABLED, simulation_mode=1):
            self.remote.evt_detailedState.flush()
            await self.csc.publish_new_detailed_state(
                TunableLaser.LaserDetailedState.PROPAGATING
            )
            await self.assert_next_sample(
                topic=self.remote.evt_detailedState,
                detailedState=TunableLaser.LaserDetailedState.PROPAGATING,
            )
            await self.remote.cmd_stopPropagateLaser.set_start(timeout=STD_TIMEOUT)
            await self.assert_next_sample(
                topic=self.remote.evt_detailedState,
                detailedState=TunableLaser.LaserDetailedState.NONPROPAGATING,
            )

    async def test_clear_laser_fault(self):
        async with self.make_csc(initial_state=salobj.State.ENABLED, simulation_mode=1):
            await self.remote.cmd_clearLaserFault.set_start(timeout=STD_TIMEOUT)


if __name__ == "__main__":
    unittest.main()
