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

import os
import pathlib
import unittest

import pytest
from lsst.ts import salobj, tunablelaser
from lsst.ts.xml.enums import TunableLaser
from parameterized import parameterized

STD_TIMEOUT = 5
TEST_CONFIG_DIR = pathlib.Path(__file__).parents[1].joinpath("tests", "data", "config")


class TunableLaserCscTestCase(salobj.BaseCscTestCase, unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        os.environ["LSST_SITE"] = "tunablelaser"
        self.laser_configs = ["", "stubbs.yaml"]
        return super().setUp()

    def basic_make_csc(self, initial_state, simulation_mode, **kwargs):
        return tunablelaser.LaserCSC(
            initial_state=initial_state,
            simulation_mode=simulation_mode,
            config_dir=TEST_CONFIG_DIR,
            override=kwargs.get("override", ""),
        )

    async def test_check_bin_script(self):
        await self.check_bin_script(
            name="TunableLaser", exe_name="run_tunablelaser", index=None
        )

    @parameterized.expand([(""), ("stubbs.yaml")])
    async def test_standard_state_transitions(self, config):
        async with self.make_csc(
            initial_state=salobj.State.STANDBY, simulation_mode=1, override=config
        ):
            await self.check_standard_state_transitions(
                enabled_commands=[
                    "changeWavelength",
                    "setOpticalConfiguration",
                    "startPropagateLaser",
                    "stopPropagateLaser",
                    "clearLaserFault",
                    "setBurstMode",
                    "setContinuousMode",
                    "setBurstCount",
                    "turnOffTempCtrl",
                    "turnOnTempCtrl",
                    "changeTempCtrlSetpoint",
                ]
            )

    @parameterized.expand([(""), ("stubbs.yaml")])
    async def test_telemetry(self, config):
        async with self.make_csc(
            initial_state=salobj.State.ENABLED, simulation_mode=1, override=config
        ):
            await self.assert_next_sample(topic=self.remote.tel_wavelength)
            await self.assert_next_sample(topic=self.remote.tel_temperature)
            await self.assert_next_sample(
                topic=self.remote.evt_summaryState,
                summaryState=salobj.State.ENABLED,
            )
            self.csc.simulator.device.propagating = "FAULT"
            await self.assert_next_sample(
                topic=self.remote.evt_summaryState,
                summaryState=salobj.State.FAULT,
            )
            assert self.csc.fc_client.response is not None
            assert self.csc.la_client.response is not None

    @parameterized.expand([(""), ("stubbs.yaml")])
    async def test_change_wavelength(self, config):
        async with self.make_csc(
            initial_state=salobj.State.ENABLED, simulation_mode=1, override=config
        ):
            await self.remote.cmd_changeWavelength.set_start(
                wavelength=700, timeout=STD_TIMEOUT
            )
            await self.assert_next_sample(
                topic=self.remote.evt_wavelengthChanged, wavelength=700
            )
            await self.assert_next_sample(
                topic=self.remote.tel_wavelength, wavelength=700, flush=True
            )
            with pytest.raises(salobj.AckError):
                if config == "":
                    wavelength = (
                        max(self.csc.model.maxi_opg.wavelength_register.accepted_values)
                        + 1
                    )
                    await self.remote.cmd_changeWavelength.set_start(
                        wavelength=wavelength, timeout=STD_TIMEOUT
                    )
                else:
                    wavelength = (
                        max(self.csc.model.midiopg.wavelength_register.accepted_values)
                        + 1
                    )
                    await self.remote.cmd_changeWavelength.set_start(
                        wavelength=wavelength, timeout=STD_TIMEOUT
                    )

            with pytest.raises(salobj.AckError):
                if config == "":
                    wavelength = (
                        min(self.csc.model.maxi_opg.wavelength_register.accepted_values)
                        - 1
                    )
                    await self.remote.cmd_changeWavelength.set_start(
                        wavelength=wavelength, timeout=STD_TIMEOUT
                    )
                else:
                    wavelength = (
                        min(self.csc.model.midiopg.wavelength_register.accepted_values)
                        - 1
                    )
                    await self.remote.cmd_changeWavelength.set_start(
                        wavelength=wavelength, timeout=STD_TIMEOUT
                    )

    @parameterized.expand([(""), ("stubbs.yaml")])
    async def test_change_alignment(self, config):
        async with self.make_csc(
            initial_state=salobj.State.ENABLED, simulation_mode=1, override=config
        ):
            await self.remote.cmd_setOpticalConfiguration.set_start(
                configuration="SCU", timeout=STD_TIMEOUT
            )
            if config == "":
                await self.assert_next_sample(
                    topic=self.remote.evt_opticalConfiguration,
                    configuration="F1 No SCU",
                )
                await self.assert_next_sample(
                    topic=self.remote.evt_opticalConfiguration,
                    configuration="SCU",
                )
                with pytest.raises(salobj.AckError):
                    await self.remote.cmd_setOpticalConfiguration.set_start(
                        configuration="Wumbo", timeout=STD_TIMEOUT
                    )

    @parameterized.expand([(""), ("stubbs.yaml")])
    async def test_start_propagate_laser(self, config):
        async with self.make_csc(
            initial_state=salobj.State.ENABLED, simulation_mode=1, override=config
        ):
            await self.assert_next_sample(
                topic=self.remote.evt_detailedState,
                detailedState=TunableLaser.LaserDetailedState.NONPROPAGATING_CONTINUOUS_MODE,
            )
            await self.remote.cmd_startPropagateLaser.set_start(timeout=STD_TIMEOUT)
            await self.assert_next_sample(
                topic=self.remote.evt_detailedState,
                detailedState=TunableLaser.LaserDetailedState.PROPAGATING_CONTINUOUS_MODE,
            )
            await self.remote.cmd_stopPropagateLaser.set_start(timeout=STD_TIMEOUT)
            await self.assert_next_sample(
                topic=self.remote.evt_detailedState,
                detailedState=TunableLaser.LaserDetailedState.NONPROPAGATING_CONTINUOUS_MODE,
            )
            await self.remote.cmd_setBurstMode.set_start(count=1, timeout=STD_TIMEOUT)
            await self.assert_next_sample(
                topic=self.remote.evt_detailedState,
                detailedState=TunableLaser.LaserDetailedState.NONPROPAGATING_BURST_MODE,
            )
            await self.remote.cmd_startPropagateLaser.set_start(timeout=STD_TIMEOUT)
            await self.assert_next_sample(
                topic=self.remote.evt_detailedState,
                detailedState=TunableLaser.LaserDetailedState.PROPAGATING_BURST_MODE,
            )

    @parameterized.expand([(""), ("stubbs.yaml")])
    async def test_stop_propagate_laser(self, config):
        async with self.make_csc(
            initial_state=salobj.State.ENABLED, simulation_mode=1, override=config
        ):
            self.remote.evt_detailedState.flush()
            await self.csc.publish_new_detailed_state(
                TunableLaser.LaserDetailedState.PROPAGATING_CONTINUOUS_MODE
            )
            await self.assert_next_sample(
                topic=self.remote.evt_detailedState,
                detailedState=TunableLaser.LaserDetailedState.PROPAGATING_CONTINUOUS_MODE,
            )
            await self.remote.cmd_stopPropagateLaser.set_start(timeout=STD_TIMEOUT)
            await self.assert_next_sample(
                topic=self.remote.evt_detailedState,
                detailedState=TunableLaser.LaserDetailedState.NONPROPAGATING_CONTINUOUS_MODE,
            )
            with pytest.raises(salobj.AckError):
                await self.remote.cmd_stopPropagateLaser.set_start(timeout=STD_TIMEOUT)
            await self.remote.cmd_startPropagateLaser.set_start(timeout=STD_TIMEOUT)
            await self.assert_next_sample(
                topic=self.remote.evt_detailedState,
                detailedState=TunableLaser.LaserDetailedState.PROPAGATING_CONTINUOUS_MODE,
            )
            await self.remote.cmd_disable.set_start(timeout=STD_TIMEOUT)
            await self.assert_next_sample(
                topic=self.remote.evt_detailedState,
                detailedState=TunableLaser.LaserDetailedState.NONPROPAGATING_CONTINUOUS_MODE,
            )

    @parameterized.expand([(""), ("stubbs.yaml")])
    async def test_clear_laser_fault(self, config):
        async with self.make_csc(
            initial_state=salobj.State.ENABLED, simulation_mode=1, override=config
        ):
            self.csc.simulator.device.laser_power = "FAULT"
            await self.remote.cmd_clearLaserFault.set_start(timeout=STD_TIMEOUT)

    @parameterized.expand([(""), ("stubbs.yaml")])
    async def test_set_burst_mode(self, config):
        async with self.make_csc(
            initial_state=salobj.State.ENABLED, simulation_mode=1, override=config
        ):
            await self.remote.cmd_setBurstMode.set_start(count=1, timeout=STD_TIMEOUT)
            await self.assert_next_sample(topic=self.remote.evt_burstModeSet)

    @parameterized.expand([(""), ("stubbs.yaml")])
    async def test_set_continuous_mode(self, config):
        async with self.make_csc(
            initial_state=salobj.State.ENABLED, simulation_mode=1, override=config
        ):
            await self.remote.cmd_setContinuousMode.set_start(timeout=STD_TIMEOUT)
            await self.assert_next_sample(topic=self.remote.evt_continuousModeSet)

    async def test_get_config_pkg(self):
        assert tunablelaser.LaserCSC.get_config_pkg() == "ts_config_mtcalsys"

    @parameterized.expand([(""), ("stubbs.yaml")])
    async def test_trigger_burst(self, config):
        async with self.make_csc(
            initial_state=salobj.State.ENABLED, simulation_mode=1, override=config
        ):
            await self.assert_next_sample(
                topic=self.remote.evt_detailedState,
                detailedState=TunableLaser.LaserDetailedState.NONPROPAGATING_CONTINUOUS_MODE,
            )
            await self.remote.cmd_setBurstMode.set_start(count=1, timeout=STD_TIMEOUT)
            await self.assert_next_sample(
                topic=self.remote.evt_detailedState,
                detailedState=TunableLaser.LaserDetailedState.NONPROPAGATING_BURST_MODE,
            )
            await self.remote.cmd_startPropagateLaser.set_start(timeout=STD_TIMEOUT)
            await self.assert_next_sample(
                topic=self.remote.evt_detailedState,
                detailedState=TunableLaser.LaserDetailedState.PROPAGATING_BURST_MODE,
            )
            await self.remote.cmd_triggerBurst.set_start(timeout=STD_TIMEOUT)

    @parameterized.expand([(""), ("stubbs.yaml")])
    async def test_tempctrl(self, config):
        async with self.make_csc(
            initial_state=salobj.State.ENABLED, simulation_mode=1, override=config
        ):
            await self.remote.cmd_turnOnTempCtrl.set_start(timeout=STD_TIMEOUT)
            await self.remote.cmd_changeTempCtrlSetpoint.set_start(
                setpoint=100, timeout=STD_TIMEOUT
            )
            await self.remote.cmd_turnOffTempCtrl.set_start(timeout=STD_TIMEOUT)

    @parameterized.expand([("disconnected_temp_ctrl.yaml")])
    async def test_unconnected_tempctrl(self, config):
        async with self.make_csc(
            initial_state=salobj.State.ENABLED, simulation_mode=1, override=config
        ):
            await self.remote.cmd_turnOnTempCtrl.set_start(timeout=STD_TIMEOUT)
            await self.remote.cmd_changeTempCtrlSetpoint.set_start(
                setpoint=100, timeout=STD_TIMEOUT
            )
            await self.remote.cmd_turnOffTempCtrl.set_start(timeout=STD_TIMEOUT)

    async def test_bad_connection(self):
        async with self.make_csc(initial_state=salobj.State.STANDBY, simulation_mode=1):
            self.csc.unstable = True
            await self.assert_next_summary_state(salobj.State.STANDBY)
            await salobj.set_summary_state(self.remote, salobj.State.DISABLED)
            await self.assert_next_summary_state(salobj.State.FAULT)
            self.csc.unstable = False
            await salobj.set_summary_state(self.remote, salobj.State.DISABLED)
            await self.assert_next_summary_state(salobj.State.STANDBY)
            await self.assert_next_summary_state(salobj.State.DISABLED)


if __name__ == "__main__":
    unittest.main()
