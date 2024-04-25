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

"""Implements CSC for the TunableLaser.

"""
__all__ = ["run_tunablelaser", "LaserCSC"]

import asyncio

from lsst.ts import salobj, utils
from lsst.ts.xml.enums import TunableLaser

from . import __version__, component, mock_server
from .config_schema import CONFIG_SCHEMA


def run_tunablelaser():
    """Run the TunableLaser CSC."""
    asyncio.run(LaserCSC.amain(index=None))


class LaserCSC(salobj.ConfigurableCsc):
    """This is the class that implements the TunableLaser CSC.

    Parameters
    ----------
    initial_state : `lsst.ts.salobj.State`, optional
        The initial state that a CSC will start up in. Only useful for unit
        tests as most CSCs will start in `salobj.State.STANDBY`
    config_dir : `pathlib.Path`, optional
        Path where the configuration files are located;
        typically used for unit tests.
    simulation_mode : `bool`, optional
        Is the laser being simulated?
    override : `str`, optional
        The name of the override config file to use, if any.

    Attributes
    ----------
    model : `Laser`
        The model of the laser component which handles the actual hardware.
    telemetry_rate : `float`
        The amount of time to wait for telemetry to publish.
    telemetry_task : `asyncio.Future`
        The task that tracks the state of the telemetry loop.
    simulator : `MainLaserServer` or `StubbsLaserServer`
        The mock simulator if in simulation mode.

    """

    valid_simulation_modes = (0, 1)
    version = __version__

    def __init__(
        self,
        initial_state=salobj.State.STANDBY,
        config_dir=None,
        simulation_mode=0,
        override="",
    ):
        super().__init__(
            name="TunableLaser",
            config_schema=CONFIG_SCHEMA,
            index=None,
            config_dir=config_dir,
            initial_state=initial_state,
            simulation_mode=simulation_mode,
            override=override,
        )
        self.model = None
        self.thermal_ctrl = None
        self.telemetry_rate = 1
        self.telemetry_task = utils.make_done_future()
        self.simulator = None
        self.thermal_ctrl_simulator = None
        self.laser_type = None

    @property
    def connected(self):
        return self.model is not None and self.model.connected

    async def telemetry(self):
        """Send out the TunableLaser's telemetry."""
        while True:
            try:
                self.log.debug("Telemetry updating")
                await self.model.read_all_registers()
                await self.thermal_ctrl.read_all_registers()
                self.log.debug(f"model={self.model}")
                self.log.debug(
                    f"detailed_state={self.evt_detailedState.data.detailedState}"
                )
                if (
                    self.model.cpu8000.power_register.register_value == "FAULT"
                    or self.model.m_cpu800.power_register.register_value == "FAULT"
                    or self.model.m_cpu800.power_register_2.register_value == "FAULT"
                ):
                    await self.fault(
                        code=TunableLaser.LaserErrorCode.HW_CPU_ERROR,
                        report=(
                            f"cpu8000 fault:{self.model.cpu8000.fault_register.register_value}"
                            f"m_cpu800 fault:{self.model.m_cpu800.fault_register.register_value}"
                            f"m_cpu800 fault2:{self.model.m_cpu800.fault_register_2.register_value}"
                        ),
                    )
                await self.tel_wavelength.set_write(
                    wavelength=float(self.model.wavelength)
                )
                await self.tel_temperature.set_write(
                    tk6_temperature=float(self.model.temperature[0]),
                    tk6_temperature_2=float(self.model.temperature[1]),
                    ldco48bp_temperature=float(self.model.temperature[2]),
                    ldco48bp_temperature_2=float(self.model.temperature[3]),
                    ldco48bp_temperature_3=float(self.model.temperature[4]),
                    m_ldco48_temperature=float(self.model.temperature[5]),
                    m_ldco48_temperature_2=float(self.model.temperature[6]),
                )
                self.log.debug("Telemetry updated")
            except Exception:
                self.log.exception("Telemetry loop failed.")
            await asyncio.sleep(self.telemetry_rate)

    def assert_substate(self, substates, action):
        """Assert that the action is happening while in the PropagatingState.

        Parameters
        ----------
        substates : `list`
            A list of allowed states
        action : `str`
            The name of the command being sent.

        Raises
        ------
        `salobj.ExpectedError`
            Raised when an action is not allowed in a substate.

        """
        if self.evt_detailedState.data.detailedState not in [
            TunableLaser.LaserDetailedState(substate) for substate in substates
        ]:
            raise salobj.ExpectedError(
                f"{action} not allowed in state {self.evt_detailedState.data.detailedState!r}"
            )

    async def handle_summary_state(self):
        """Handle the summary state transitons."""
        if self.disabled_or_enabled:
            if self.simulation_mode:
                if self.simulator is None:
                    self.log.debug("Starting simulator.")
                    simulatorcls = getattr(
                        mock_server, f"{type(self.model).__name__}Server"
                    )
                    self.simulator = simulatorcls()
                    self.log.debug(f"Chose {self.simulator=}")
                    await self.simulator.start_task

                    self.thermal_ctrl_simulator = mock_server.TempCtrlServer(
                        host=self.thermal_ctrl.host
                    )
                    await self.thermal_ctrl_simulator.start_task
                    self.thermal_ctrl.port = self.thermal_ctrl_simulator.port

            if not self.connected and self.model is not None:
                await self.evt_detailedState.set_write(
                    detailedState=TunableLaser.LaserDetailedState.NONPROPAGATING
                )
                await self.model.connect()
                if self.laser_type == "Main":
                    await self.model.set_optical_configuration(self.optical_alignment)
                await self.thermal_ctrl.connect()
            if (
                self.summary_state == salobj.State.DISABLED
                and self.model.is_propagating
            ):
                await self.model.stop_propagating()
                await self.publish_new_detailed_state(
                    TunableLaser.LaserDetailedState.NONPROPAGATING
                )
            if self.telemetry_task.done():
                self.telemetry_task = asyncio.create_task(self.telemetry())
        else:
            if self.model is not None and self.model.connected:
                await self.model.disconnect()
                self.model = None
                await self.thermal_ctrl.disconnect()
                self.thermal_ctrl = None
            if self.simulator is not None:
                await self.simulator.close()
                self.simulator = None
                await self.thermal_ctrl_simulator.close()
                self.thermal_ctrl_simulator = None
            self.telemetry_task.cancel()

    async def do_setBurstMode(self, data):
        """Set burst mode for the laser.

        Burst mode changes the propagation to pulse the laser with increased
        power at a regular interval.

        Parameters
        ----------
        data : `DataType`
            The command data.
        """
        self.assert_enabled()
        if self.connected:
            await self.model.set_burst_mode(data.count)
            await self.evt_burstModeSet.set_write()
        else:
            raise salobj.ExpectedError("Not connected.")

    async def do_setContinuousMode(self, data):
        """Set continuous mode for the laser.

        Continuous mode changes the propagation to pulse continuously at a
        regular power level.

        Parameters
        ----------
        data : `DataType`
            The command data.
        """
        self.assert_enabled()
        if self.connected:
            await self.model.set_continuous_mode()
            await self.evt_continuousModeSet.set_write()
        else:
            raise salobj.ExpectedError("Not connected.")

    async def do_changeWavelength(self, data):
        """Change the wavelength of the laser.

        Parameters
        ----------
        data
        """
        self.assert_enabled()
        if self.connected:
            await self.model.change_wavelength(data.wavelength)
            await self.evt_wavelengthChanged.set_write(wavelength=data.wavelength)
        else:
            raise salobj.ExpectedError("Not connected")

    async def do_startPropagateLaser(self, data):
        """Change the state to the Propagating State of the laser.

        Parameters
        ----------
        data
        """
        self.assert_enabled()
        self.assert_substate(
            [
                TunableLaser.LaserDetailedState.NONPROPAGATING,
                TunableLaser.LaserDetailedState.PROPAGATING_BURST_MODE_WAITING_FOR_TRIGGER,
            ],
            "startPropagateLaser",
        )
        if self.connected:
            await self.model.set_output_energy_level("MAX")
            await self.model.start_propagating(data)
        else:
            raise salobj.ExpectedError("Not connected.")

    async def do_stopPropagateLaser(self, data):
        """Stop the Propagating State of the laser.

        Parameters
        ----------
        data
        """
        self.assert_enabled()
        self.assert_substate(
            [
                TunableLaser.LaserDetailedState.PROPAGATING,
                TunableLaser.LaserDetailedState.PROPAGATING_BURST_MODE_WAITING_FOR_TRIGGER,
            ],
            "stopPropagateLaser",
        )
        if self.connected:
            await self.model.stop_propagating()
            await self.publish_new_detailed_state(
                TunableLaser.LaserDetailedState.NONPROPAGATING
            )
        else:
            raise salobj.ExpectedError("Not connected.")

    async def do_clearLaserFault(self, data):
        """Clear the hardware fault state of the laser by turning the power
        register off.

        Parameters
        ----------
        data
        """
        self.assert_enabled()
        if self.connected:
            await self.model.clear_fault()
        else:
            raise salobj.ExpectedError("Not connected.")

    async def do_triggerBurst(self, data):
        """Trigger a burst."""
        self.assert_enabled()
        self.assert_substate(
            [
                TunableLaser.LaserDetailedState.PROPAGATING_BURST_MODE_WAITING_FOR_TRIGGER
            ],
            "Trigger",
        )
        await self.model.trigger_burst()

    async def do_changeTempCtrlSetpoint(self, data):
        """Change the set point of the laser thermal reader."""
        self.assert_enabled()
        if self.connected:
            await self.thermal_ctrl.laser_thermal_change_set_point(value=data.setpoint)
        else:
            raise salobj.ExpectedError("Not connected.")

    async def do_turnOffTempCtrl(self, data):
        """Turn off the run mode of the laser thermal reader."""
        self.assert_enabled()
        if self.connected:
            await self.thermal_ctrl.laser_thermal_turn_off()
        else:
            raise salobj.ExpectedError("Not connected.")

    async def do_turnOnTempCtrl(self, data):
        """Turn on the run mode of the laser thermal reader."""
        self.assert_enabled()
        if self.connected:
            await self.thermal_ctrl.laser_thermal_turn_on()
        else:
            raise salobj.ExpectedError("Not connected.")

    async def do_setOpticalConfiguration(self, data):
        """Change Optical Alignment of the laser.
        Parameters
        ----------
        data - with property 'configuration' setting optical
               alignment of the laser.
        """
        self.assert_enabled()
        if self.connected:
            if self.laser_type == "Main":  # only main laser can do this
                await self.model.set_optical_configuration(data.configuration)
                await self.evt_opticalConfiguration.set_write(
                    configuration=data.configuration
                )
        else:
            raise salobj.ExpectedError("Not connected")

    async def publish_new_detailed_state(self, new_sub_state):
        """Publish the updated detailed state.

        Parameters
        ----------
        new_sub_state : `LaserDetailedState`
            The new sub state to publish.
        """
        new_sub_state = TunableLaser.LaserDetailedState(new_sub_state)
        await self.evt_detailedState.set_write(detailedState=new_sub_state)

    async def configure(self, config):
        """Configure the CSC."""
        self.log.debug(f"config={config}")
        self.log.debug(f"Connecting to laser {config.type}")
        self.laser_type = config.type
        lasercls = getattr(component, f"{config.type}Laser")
        self.model = lasercls(csc=self, simulation_mode=bool(self.simulation_mode))
        self.optical_alignment = config.optical_configuration
        await self.model.configure(config)

        self.thermal_ctrl = component.TemperatureCtrl(
            csc=self,
            host=config.temp_ctrl["host"],
            port=config.temp_ctrl["port"],
            simulation_mode=bool(self.simulation_mode),
        )

    @staticmethod
    def get_config_pkg():
        """Return the configuration package name."""
        return "ts_config_mtcalsys"

    async def close_tasks(self):
        """Tasks to perform before closing the CSC.

        * Cancel telemetry
        * If laser is propagating, stop it.
        * Disconnect from the laser
        * If simulator is running, shut it off
        """
        await super().close_tasks()
        self.telemetry_task.cancel()
        if self.model is not None:
            if self.model.is_propagating:
                await self.model.stop_propagating()
            await self.model.disconnect()
            self.model = None
        if self.thermal_ctrl is not None:
            await self.thermal_ctrl.disconnect()
            self.thermal_ctrl = None
        if self.simulator is not None:
            await self.simulator.close()
            self.simulator = None
        if self.thermal_ctrl_simulator is not None:
            await self.thermal_ctrl_simulator.close()
            self.thermal_ctrl_simulator = None
