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

__all__ = ["MainLaser", "StubbsLaser", "TemperatureCtrl"]

import asyncio

from lsst.ts.xml.enums.TunableLaser import LaserDetailedState

from . import canbus_modules, interfaces
from .enums import Mode, Power


class MainLaser(interfaces.Laser):
    """The class that implements the TunableLaser component.

    Parameters
    ----------
    csc : `LaserCSC`
        The CSC object.
    simulation_mode : `bool`
        A flag which tells the component to initialize into simulation mode or
        not.
    encoding : `str`
        The type of encoding to use.
    terminator : `bytes`
        The terminating characters for messages sent/received.

    Attributes
    ----------
    laser_id : `int`
        The ID of the laser
    csc : `LaserCSC`
        Reference to the CSC object.
    cpu8000 : `CPU8000`
        Controls the CPU8000 laser :term:`module`.
    m_cpu800 : `MCPU800`
        Controls the M_CPU800 laser module.
    llpmku : `LLPMKU`
        Controls the llPKMu laser module.
    maxi_opg : `MaxiOPG`
        Controls the MaxiOPG laser module.
    tk6 : `TK6`
        Controls the TK6 laser module.
    hv40w : `HV40W`
        Controls the HV40W laser module.
    delay_lin : `DelayLin`
        Controls the DelayLin laser module.
    mini_opg : `MiniOPG`
        Controls the MiniOPG laser module.
    ldco48bp : `LDCO48BP`
        Controls the LDCO48BP laser module.
    m_ldco48 : `MLDCO48`
        Controls the LDCO48 laser module.
    laser_warmup_delay : `int`
        The warmup delay before stating that the laser is propagating.
    lock : `asyncio.Lock`
        Lock the read/write operation.


    """

    def __init__(
        self, csc, simulation_mode=False, encoding="ascii", terminator=b"\x03"
    ):
        super().__init__(
            csc=csc,
            terminator=terminator,
            encoding=encoding,
            simulation_mode=simulation_mode,
        )
        self.laser_id = 1
        self.cpu8000 = canbus_modules.CPU8000(component=self)
        self.m_cpu800 = canbus_modules.MCPU800(component=self)
        self.llpmku = canbus_modules.LLPMKU(component=self)
        self.maxi_opg = canbus_modules.MaxiOPG(component=self)
        self.tk6 = canbus_modules.TK6(component=self)
        self.hv40w = canbus_modules.HV40W(component=self, laser_id=self.laser_id)
        self.delay_lin = canbus_modules.DelayLin(component=self, laser_id=self.laser_id)
        self.mini_opg = canbus_modules.MiniOPG(component=self)
        self.ldco48bp = canbus_modules.LDCO48BP(component=self, laser_id=self.laser_id)
        self.m_ldcO48 = canbus_modules.MLDCO48(component=self)
        self.laser_warmup_delay = 10
        self.lock = asyncio.Lock()

    @property
    def is_propagating(self):
        if self.m_cpu800.power_register_2.register_value == Power.ON:
            return True
        else:
            return False

    @property
    def wavelength(self):
        return self.maxi_opg.wavelength_register.register_value

    @property
    def temperature(self):
        return (
            self.tk6.display_temperature_register.register_value,
            self.tk6.display_temperature_register_2.register_value,
            self.ldco48bp.display_temperature_register.register_value,
            self.ldco48bp.display_temperature_register_2.register_value,
            self.ldco48bp.display_temperature_register_3.register_value,
            self.m_ldcO48.display_temperature_register.register_value,
            self.m_ldcO48.display_temperature_register_2.register_value,
        )

    async def change_wavelength(self, wavelength):
        """Change the wavelength of the laser.

        Parameters
        ----------
        wavelength : `float`
            The wavelength to change to.

            :Units: nanometers
        """
        self.log.debug("Changing wavelength")
        await self.maxi_opg.change_wavelength(wavelength)

    async def set_optical_configuration(self, optical_configuration):
        """Change the optical alignment of the laser.

        Parameters
        ----------
        optical_configuration: `str`, {straight-through,F1,F2}
            The optical alignment to switch to.
        """
        self.maxi_opg.optical_alignment = optical_configuration
        self.log.debug(
            f"Set optical alignment to {optical_configuration}"
            f"Optical alignment is {self.maxi_opg.optical_alignment}"
        )
        await self.maxi_opg.set_configuration()
        await self.csc.evt_opticalConfiguration.set_write(
            configuration=optical_configuration
        )

    async def set_output_energy_level(self, output_energy_level):
        """Set the output energy level of the laser.

        Parameters
        ----------
        output_energy_level : `str`, {OFF,Adjust,MAX}
            The energy level to set the laser to.

            * OFF: Output energy is off.
            * Adjust: A mode for calibrating the laser.
            * MAX: The maximum energy output of the laser.
        """
        self.log.debug(f"Changing output energy level={output_energy_level}")
        await self.m_cpu800.set_output_energy_level(output_energy_level)

    async def trigger_burst(self):
        """Trigger a burst.

        Raises
        ------
        ValueError
            Raised when mode parameter is not in list of accepted values.
        """
        await self.m_cpu800.set_propagation_mode(Mode.TRIGGER)

    async def set_burst_mode(self, count):
        """Set the propagation mode to pulse the laser at regular intervals.

        Parameters
        ----------
        count : `int`
            The amount of times to pulse the laser.
            Range is from 1 to 50000.

        Raises
        ------
        ValueError
            Raised when the count parameter falls outside of the
            accepted range.
        """
        await self.m_cpu800.set_propagation_mode(Mode.BURST)
        await self.m_cpu800.set_burst_count(count)

    async def set_continuous_mode(self):
        """Set the propagation mode to continuously pulse the laser."""
        await self.m_cpu800.set_propagation_mode(Mode.CONTINUOUS)

    async def set_burst_count(self, count):
        """Set the burst count of the laser.

        Parameters
        ----------
        count : `int`
            The amount to pulse the laser.
        """
        await self.m_cpu800.set_burst_count(count)
        await self.csc.evt_burstCountSet.set_write(count=count)

    async def start_propagating(self, data):
        """Start propagating the beam of the laser."""
        await self.m_cpu800.start_propagating()
        await self.csc.cmd_startPropagateLaser.ack_in_progress(
            data=data, timeout=self.laser_warmup_delay
        )
        await asyncio.sleep(self.laser_warmup_delay)  # laser warmup delay
        if (
            self.m_cpu800.continous_burst_mode_trigger_burst_register.register_value
            == Mode.BURST
        ):
            await self.csc.publish_new_detailed_state(
                LaserDetailedState.PROPAGATING_BURST_MODE
            )
        elif (
            self.m_cpu800.continous_burst_mode_trigger_burst_register.register_value
            == Mode.CONTINUOUS
        ):
            await self.csc.publish_new_detailed_state(
                LaserDetailedState.PROPAGATING_CONTINUOUS_MODE
            )
        else:
            raise RuntimeError(
                f"""{self.m_cpu800.continous_burst_mode_trigger_burst_register.register_value}
                not in list of {list(Mode)} valid laser modes."""
            )

    async def stop_propagating(self):
        """Stop propagating the beam of the laser"""
        await self.m_cpu800.stop_propagating()

    async def clear_fault(self):
        """Clear the fault state of the laser."""
        if self.m_cpu800.power_register_2.register_value == "FAULT":
            await self.m_cpu800.power_register_2.set_register_value()

    async def read_all_registers(self):
        """Publish the module's registers' values."""
        await self.cpu8000.update_register()
        await self.m_cpu800.update_register()
        await self.llpmku.update_register()
        await self.maxi_opg.update_register()
        await self.mini_opg.update_register()
        await self.tk6.update_register()
        await self.hv40w.update_register()
        await self.delay_lin.update_register()
        await self.ldco48bp.update_register()
        await self.m_ldcO48.update_register()

    async def configure(self, config):
        """Set the configuration for the TunableLaser."""
        self.log.debug("Setting config.")

        self.host = config.host
        self.port = config.port
        self.maxi_opg.wavelength_register.accepted_values = range(
            config.wavelength["min"], config.wavelength["max"]
        )
        self.log.debug(
            f"Set min={config.wavelength['min']} & max={config.wavelength['max']} wavelength range."
        )
        self.maxi_opg.optical_alignment = config.optical_configuration
        self.log.debug(
            f"Set optical alignment to {config.optical_configuration}"
            f"Optical alignment is {self.maxi_opg.optical_alignment}"
        )

    def __str__(self):
        return (
            f"{self.cpu8000} {self.m_cpu800} {self.llpmku} {self.maxi_opg} {self.mini_opg} {self.tk6}"
            f"{self.hv40w} {self.delay_lin} {self.ldco48bp} {self.m_ldcO48}"
        )


class StubbsLaser(interfaces.Laser):
    """Implement the Stubbs NT-252 laser.

    Parameters
    ----------
    csc : `LaserCSC`
        The CSC object.
    terminator : `bytes`
        The terminating characters for sent/received messages.
    encoding : `str`
        The type of encoding to use.
    simulation_mode : `bool`
        Is the laser in simulation mode?

    Attributes
    ----------
    laser_id : `int`
        The ID of the laser.
    midiopg : `hardware.MidiOPG`
        The MidiOPG module.
    m_cpu800 : `hardware.MCPU800`
        The MCPU800 module.
    cpu8000 : `hardware.CPU8000`
        The CPU8000 module.
    tk6 : `hardware.TK6`
        The TK6 module.
    hv40w : `hardware.HV40W`
        The HV40W module.
    delay_lin : `hardware.DelayLin`
        The DelayLin module.
    ldco48bp : `hardware.LDCO48BP`
        The LDCO48BP module.
    m_ldc048 : `hardware.MLDCO48`
        The MLDCO48 module.
    laser_warmup_delay : `int`
        A delay for publishing propagation for warmup.
    lock : `asyncio.Lock`
        A lock for writing/reading messages.
    """

    def __init__(
        self, csc, terminator=b"\x03", encoding="ascii", simulation_mode=False
    ) -> None:
        super().__init__(
            csc=csc,
            terminator=terminator,
            encoding=encoding,
            simulation_mode=simulation_mode,
        )
        self.laser_id = 2
        self.midiopg = canbus_modules.MidiOPG(component=self)
        self.m_cpu800 = canbus_modules.MCPU800(component=self)
        self.cpu8000 = canbus_modules.CPU8000(component=self)
        self.tk6 = canbus_modules.TK6(component=self)
        self.hv40w = canbus_modules.HV40W(component=self, laser_id=self.laser_id)
        self.delay_lin = canbus_modules.DelayLin(component=self, laser_id=self.laser_id)
        self.ldco48bp = canbus_modules.LDCO48BP(component=self, laser_id=self.laser_id)
        self.m_ldcO48 = canbus_modules.MLDCO48(component=self)
        self.laser_warmup_delay = 10
        self.lock = asyncio.Lock()

    @property
    def is_propagating(self):
        if self.m_cpu800.power_register_2.register_value == "ON":
            return True
        else:
            return False

    @property
    def wavelength(self):
        return self.midiopg.wavelength_register.register_value

    @property
    def temperature(self):
        return (
            self.tk6.display_temperature_register.register_value,
            self.tk6.display_temperature_register_2.register_value,
            self.ldco48bp.display_temperature_register.register_value,
            self.ldco48bp.display_temperature_register_2.register_value,
            self.ldco48bp.display_temperature_register_3.register_value,
            self.ldco48bp.display_temperature_register_4.register_value,
            self.m_ldcO48.display_temperature_register.register_value,
            self.m_ldcO48.display_temperature_register_2.register_value,
        )

    async def change_wavelength(self, wavelength):
        await self.midiopg.change_wavelength(wavelength)

    async def set_output_energy_level(self, output_energy_level):
        await self.m_cpu800.set_output_energy_level(output_energy_level)

    async def trigger_burst(self):
        """Trigger a burst.

        Raises
        ------
        ValueError
            Raised when mode parameter is not in list of accepted values.
        """
        await self.m_cpu800.set_propagation_mode(Mode.TRIGGER)

    async def set_burst_mode(self, count):
        """Set the propagation mode to pulse the laser at regular intervals.

        Parameters
        ----------
        count : `int`
            The amount of times to pulse the laser.
            Range is from 1 to 50000.

        Raises
        ------
        ValueError
            Raised when the count parameter falls outside of the
            accepted range.
        """
        await self.m_cpu800.set_propagation_mode(Mode.BURST)
        await self.m_cpu800.set_burst_count(count)
        await self.csc.evt_burstCountSet.set_write(count=count)

    async def set_continuous_mode(self):
        """Set the propagation mode to continuously pulse the laser."""
        await self.m_cpu800.set_propagation_mode(Mode.CONTINUOUS)

    async def set_burst_count(self, count):
        """Set the burst count of the laser.

        Parameters
        ----------
        count : `int`
            The amount to pulse the laser.
        """
        await self.m_cpu800.set_burst_count(count)
        await self.csc.evt_burstCountSet.set_write(count=count)

    async def start_propagating(self, data):
        """Start propagating the beam of the laser."""
        await self.m_cpu800.start_propagating()
        await self.csc.cmd_startPropagateLaser.ack_in_progress(
            data=data, timeout=self.laser_warmup_delay
        )
        await asyncio.sleep(self.laser_warmup_delay)  # laser warmup delay
        if (
            self.m_cpu800.continous_burst_mode_trigger_burst_register.register_value
            == Mode.BURST
        ):
            await self.csc.publish_new_detailed_state(
                LaserDetailedState.PROPAGATING_BURST_MODE
            )
        elif (
            self.m_cpu800.continous_burst_mode_trigger_burst_register.register_value
            == Mode.CONTINUOUS
        ):
            await self.csc.publish_new_detailed_state(
                LaserDetailedState.PROPAGATING_CONTINUOUS_MODE
            )
        else:
            raise RuntimeError(
                f"""{self.m_cpu800.continous_burst_mode_trigger_burst_register.register_value}
                not in list of {list(Mode)} valid laser modes."""
            )

    async def stop_propagating(self):
        """Stop propagating the beam of the laser"""
        await self.m_cpu800.stop_propagating()

    async def clear_fault(self):
        """Clear the fault state of the laser."""
        if self.m_cpu800.power_register_2.register_value == "FAULT":
            await self.m_cpu800.power_register_2.set_register_value()

    async def configure(self, config):
        self.log.debug("Setting config.")
        self.host = config.host
        self.port = config.port

        self.midiopg.wavelength_register.accepted_values = range(
            config.wavelength["min"], config.wavelength["max"]
        )
        self.log.debug(
            f"Set min={config.wavelength['min']} & max={config.wavelength['max']} wavelength range."
        )
        # self.maxi_opg.optical_alignment = config.optical_configuration
        # self.log.debug(
        #     f"Set optical alignment to {config.optical_configuration}"
        #     f"Optical alignment is {self.maxi_opg.optical_alignment}"
        # ) PF: Not sure about this either

    async def read_all_registers(self):
        await self.midiopg.update_register()
        await self.cpu8000.update_register()
        await self.m_cpu800.update_register()
        await self.tk6.update_register()
        await self.hv40w.update_register()
        await self.delay_lin.update_register()
        await self.ldco48bp.update_register()
        await self.m_ldcO48.update_register()


class TemperatureCtrl(interfaces.CompoWayFModule):
    """Implement the Omron Temperature Controller.

    Parameters
    ----------
    csc : `LaserCSC`
    The CSC object.
    host : `string`
    The IP address of the temp controller
    port : `int`
    The port of the temp controller
    terminator : `bytes`
    The terminating characters for sent/received messages.
    encoding : `str`
    The type of encoding to use.
    simulation_mode : `bool`
    Is the interface in simulation mode?

    Attributes
    ----------
    lock : `asyncio.Lock`
    A lock for writing/reading messages.
    host : `string`
    the host for the temp controller to connect to during simulation mode
    """

    def __init__(
        self,
        csc,
        host="127.0.0.1",
        port=50,
        terminator=b"\x03",
        encoding="ascii",
        simulation_mode=False,
    ) -> None:
        super().__init__(
            csc=csc,
            terminator=terminator,
            encoding=encoding,
            simulation_mode=simulation_mode,
        )
        self.lock = asyncio.Lock()

        # if host is not valid IP address assume its unconnected
        if str(host).lower() != "none":
            self.host = host
            self.e5dc_b = canbus_modules.E5DCB(
                component=self, simulation_mode=simulation_mode
            )
        else:
            self.log.error(
                f"Host address given to Temp Ctrl not valid, assuming unconnected: {host}"
            )
            self.host = None
            self.e5dc_b = None
        self.port = port

    @property
    def temperature(self):
        if self.e5dc_b is not None:
            return (self.e5dc_b.set_point_register.register_value,)
        else:
            return (-1,)

    async def laser_thermal_turn_on(self):
        if self.e5dc_b is not None:
            await self.e5dc_b.run_stop_register.set_register_value(True)
        else:
            self.log.error(
                "Tried to laser_thermal_turn_on but thermal ctrler is unconnected."
            )

    async def laser_thermal_turn_off(self):
        if self.e5dc_b is not None:
            await self.e5dc_b.run_stop_register.set_register_value(False)
        else:
            self.log.error(
                "Tried to laser_thermal_turn_off but thermal ctrler is unconnected."
            )

    async def laser_thermal_change_set_point(self, value):
        if self.e5dc_b is not None:
            await self.e5dc_b.set_point_register.set_register_value(value)
        else:
            self.log.error(
                "Tried to laser_thermal_change_set_point but thermal ctrler is unconnected."
            )

    async def configure(self, config):
        self.log.debug("Setting config.")
        self.host = config.host
        self.port = config.port

    async def read_all_registers(self):
        if self.e5dc_b is not None:
            await self.e5dc_b.update_register()
        else:
            self.log.warning(
                "Tried to update_register but thermal ctrler is unconnected."
            )
