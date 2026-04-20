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

"""Implements classes corresponding to modules for the TunableLaser.

These classes correspond to one module inside of the TunableLaser.
Each class contains child registers that have values that can be read and
sometimes set. Transport is handled by the owning laser or temperature
controller, not by the modules themselves.

Notes
-----
These classes are based on the REMOTECONTROL.csv file provided by the vendor.

"""

__all__ = [
    "CPU8000",
    "MCPU800",
    "LLPMKU",
    "MaxiOPG",
    "MiniOPG",
    "TK6",
    "HV40W",
    "LDCO48BP",
    "MLDCO48",
    "DelayLin",
    "MidiOPG",
    "E5DCB",
]
import logging

from . import interfaces
from .compoway_register import CompoWayFDataRegister, CompoWayFOperationRegister
from .enums import Mode, OpticalConfiguration, Output, Power
from .register import AsciiRegister


class CPU8000(interfaces.CanbusModule):
    """Implement the CPU8000 laser module which displays information about
    the primary CPU of the laser.

    This module contains registers about the power state, fault code and the
    current.

    Attributes
    ----------
    log : `logging.Logger`
        The log for the class.
    name : `str`
        Name of the module.
    id : `int`
        The ID of the module.
    power_register : `AsciiRegister`
        Handles the "Power" register for this module.
    display_current_register : `AsciiRegister`
        Handles the "Display current" register.
    fault_register : `AsciiRegister`
        Handles the "Fault code" register.


    """

    def __init__(self, simulation_mode=False):
        super().__init__()
        self.log = logging.getLogger("CPU8000")
        self.name = "CPU8000"
        self.id = 16
        self.power_register = AsciiRegister(
            module_name=self.name,
            module_id=self.id,
            register_name="Power",
        )
        self.display_current_register = AsciiRegister(
            module_name=self.name,
            module_id=self.id,
            register_name="Display Current",
        )
        self.fault_register = AsciiRegister(
            module_name=self.name,
            module_id=self.id,
            register_name="Fault code",
        )
        self.log.debug(f"{self.name} Module initialized")

    async def update_register(self, read_register):
        """Publish the registers located inside of this module.

        Returns
        -------
        None

        """
        await super().update_register(read_register)

    def __repr__(self):
        """Represent the register in prettier format."""
        return f"CPU8000:\n {self.power_register}\n {self.display_current_register}\n {self.fault_register}\n"


class MCPU800(interfaces.CanbusModule):
    """Implement the MCPU800 laser module which contains registers for
    controlling aspects of the propagation of the laser.

    Attributes
    ----------
    name : `str`
        The name of the module.
    id : `int`
        The id of the module.
    id_2 : `int`
        The second id of the module.
    power_register : `AsciiRegister`
        Handles the "Power" register.
    display_current_register : `AsciiRegister`
        Handles the "Display current" register.
    fault_register : `AsciiRegister`
        Handles the "Fault code" register.
    power_register_2 : `AsciiRegister`
        Handles the "Power" register which handles the propagation.
    display_current_register_2 : `AsciiRegister`
        Handles the "Display current" register.
    fault_register_2 : `AsciiRegister`
        Handles the "Fault code" register.
    continous_burst_mode_trigger_burst_register : `AsciiRegister`
        Handles the "Continuous %f Burst mode %f Trigger burst" register.
    output_energy_level_register : `AsciiRegister`
        Handles the "Output energy level" register.
    frequency_divider_register : `AsciiRegister`
        Handles the "frequency divider" register.
    burst_pulse_left_register : `AsciiRegister`
        Handles the "Burst pulse left" register.
    qsw_adjustment_output_delay_register : `AsciiRegister`
        Handles the "qsw adjustment output delay" register.
    repetition_rate_register : `AsciiRegister`
        Handles the "Repetition rate" register.
    synchronization_mode_register : `AsciiRegister`
        Handles the "Synchronization mode" register.
    burst_length_register : `AsciiRegister`
        Handles the "Burst length" register.
        Set the count of bursts during propagation.
        Accepts values between 1 and 50,000

    """

    def __init__(self, simulation_mode=False):
        super().__init__()
        self.name = "M_CPU800"
        self.id = 17
        self.id_2 = 18
        self.power_register = AsciiRegister(
            module_name=self.name,
            module_id=self.id,
            register_name="Power",
        )
        self.display_current_register = AsciiRegister(
            module_name=self.name,
            module_id=self.id,
            register_name="Display Current",
        )
        self.fault_register = AsciiRegister(
            module_name=self.name,
            module_id=self.id,
            register_name="Fault code",
        )

        self.power_register_2 = AsciiRegister(
            module_name=self.name,
            module_id=self.id_2,
            register_name="Power",
            read_only=False,
            accepted_values=list(Power),
        )
        self.display_current_register_2 = AsciiRegister(
            module_name=self.name,
            module_id=self.id_2,
            register_name="Display Current",
        )
        self.fault_register_2 = AsciiRegister(
            module_name=self.name,
            module_id=self.id_2,
            register_name="Fault code",
        )
        self.continous_burst_mode_trigger_burst_register = AsciiRegister(
            module_name=self.name,
            module_id=self.id_2,
            register_name="Continuous %2F Burst mode %2F Trigger burst",
            read_only=False,
            accepted_values=list(Mode),
        )
        self.output_energy_level_register = AsciiRegister(
            module_name=self.name,
            module_id=self.id_2,
            register_name="Output Energy level",
            read_only=False,
            accepted_values=list(Output),
        )
        self.frequency_divider_register = AsciiRegister(
            module_name=self.name,
            module_id=self.id_2,
            register_name="Frequency divider",
            read_only=False,
            accepted_values=range(1, 5001),
        )
        self.burst_pulse_left_register = AsciiRegister(
            module_name=self.name,
            module_id=self.id_2,
            register_name="Burst pulses to go",
        )
        self.qsw_adjustment_output_delay_register = AsciiRegister(
            module_name=self.name,
            module_id=self.id_2,
            register_name="QSW Adjustment output delay",
        )
        self.repetition_rate_register = AsciiRegister(
            module_name=self.name,
            module_id=self.id_2,
            register_name="Repetition rate",
        )
        self.synchronization_mode_register = AsciiRegister(
            module_name=self.name,
            module_id=self.id_2,
            register_name="Synchronization mode",
        )
        self.burst_length_register = AsciiRegister(
            module_name=self.name,
            module_id=self.id_2,
            register_name="Burst length",
            read_only=False,
            accepted_values=range(1, 50001),
        )

    def start_propagating(self):
        """Start the propagation of the laser.

        If used while the laser is propagating, no discernable effect occurs.

        Returns
        -------
        None

        """
        return self.power_register_2, Power.ON

    def stop_propagating(self):
        """Stop the propagation of the laser.

        If used while the laser is not propagating, no discernable effect
        occurs.

        Returns
        -------
        None

        """
        return self.power_register_2, Power.OFF

    def set_output_energy_level(self, value):
        """Set the output energy level for the laser.

        Parameters
        ----------
        value : `str`, {OFF,Adjust,MAX}

        Returns
        -------
        None
        """
        return self.output_energy_level_register, value

    def set_propagation_mode(self, value):
        """Set the propagation mode of the laser.

        value : `str`, {Continuous, Burst, Trigger}
            The mode to be set
            Continuous: Continuous pulse
            Burst: Pulses a set number of times at regular interval
            Trigger: Trigger a pulse using an external device
            Trigger has not been used as we have no source.
        """
        return self.continous_burst_mode_trigger_burst_register, Mode(value)

    def set_burst_count(self, value):
        """Set the burst count for the laser when in burst mode.

        Parameters
        ----------
        value : `int`
            The amount of pulses to perform.
            Accepts values between 1 and 50000
        """
        return self.burst_length_register, value

    async def update_register(self, read_register):
        """Publish the register values of the module.

        Returns
        -------
        None

        """
        await super().update_register(read_register)

    def __repr__(self):
        """Represent the register in prettier format."""
        return (
            f"M_CPU800:\n {self.power_register}\n {self.display_current_register}\n"
            f"{self.fault_register}\n {self.power_register_2}\n {self.display_current_register_2}\n"
            f"{self.fault_register_2}\n {self.continous_burst_mode_trigger_burst_register}\n"
            f"{self.output_energy_level_register}\n {self.frequency_divider_register}\n"
            f"{self.burst_pulse_left_register}\n {self.qsw_adjustment_output_delay_register}\n"
            f"{self.repetition_rate_register}\n {self.synchronization_mode_register}\n"
            f"{self.burst_length_register}\n"
        )


class LLPMKU(interfaces.CanbusModule):
    """Implement the LLPMKU laser module which contains a register for power.

    Attributes
    ----------
    name : `str`
        The name of the module.
    id : `int`
        The id of the module.
    power_register : `AsciiRegister`
        Handles the "Power" register.

    """

    def __init__(self, simulation_mode=False):
        super().__init__()
        self.name = "11PMKu"
        self.id = 54
        self.power_register = AsciiRegister(
            module_name=self.name,
            module_id=self.id,
            register_name="Power",
        )

    async def update_register(self, read_register):
        """Publish the register values of the module.

        Returns
        -------
        None

        """
        await super().update_register(read_register)

    def __repr__(self):
        """Represent the register in prettier format."""
        return f"11PMKu:\n {self.power_register}"


class MidiOPG(interfaces.CanbusModule):
    """Implement the MidiOPG module which controls the wavelength register.

    Attributes
    ----------
    name : `str`
        The name of the canbus module.
    id : `int`
        The ID of the canbus module.
    wavelength_register : `AsciiRegister`
        The register that controls the wavelength.
    """

    def __init__(self) -> None:
        super().__init__()
        self.name = "MidiOPG"
        self.id = 31
        self.wavelength_register = AsciiRegister(
            module_name=self.name,
            module_id=self.id,
            register_name="WaveLength",
            read_only=False,
            accepted_values=range(1, 2600),
        )

    def change_wavelength(self, value):
        """Change wavelength.

        Parameters
        ----------
        value : `float`
            The wavelength value.
        """
        return self.wavelength_register, value

    async def update_register(self, read_register):
        """Update all registers."""
        await super().update_register(read_register)

    def __repr__(self):
        """Represent the register in prettier format."""
        return f"{self.name}:\n {self.wavelength_register}\n"


class MaxiOPG(interfaces.CanbusModule):
    """Implement the MaxiOPG laser module which contains registers for
    optical alignment and wavelength.



    Parameters
    ----------
    simulation_mode : `bool`
        False for normal operation, true for simulation operation.
    configuration : `str`
        Used for unit testing, changes the laser direction between the
        spectral cleaning unit or not
        Requires a physical change on the hardware which is why it's hardcoded
        in the class.

    Attributes
    ----------
    name : `str`
        The name of the module.
    id : `int`
        The id of the module.
    wavelength_register : `AsciiRegister`
        Handles the "WaveLength" register.
    configuration_register : `AsciiRegister`
        Handles the "Configuration" register.
    """

    def __init__(self, simulation_mode=False):
        super().__init__()
        self.name = "MaxiOPG"
        self.id = 31
        self.optical_alignment = OpticalConfiguration.NO_SCU
        self.wavelength_register = AsciiRegister(
            module_name=self.name,
            module_id=self.id,
            register_name="WaveLength",
            read_only=False,
            accepted_values=range(300, 1100),
        )
        self.configuration_register = AsciiRegister(
            module_name=self.name,
            module_id=self.id,
            register_name="Configuration",
            read_only=False,
            accepted_values=list(OpticalConfiguration),
        )

    def change_wavelength(self, wavelength):
        """Change the wavelength of the laser.

        Parameters
        ----------
        wavelength : `float`
            The wavelength to change to.

        Returns
        -------
        None

        """
        return self.wavelength_register, wavelength

    def set_configuration(self):
        """Set the configuration of the output of the laser

        Parameters
        ----------
        configuration : `str`, {Det,No SCU,SCU,F1 SCU,F2 SCU,F1 No SCU,
        F2 No SCU}
            These are the output points that can be chosen.
            Note that if SCU/No SCU is set in the controller, then only those
            options with the term can be chosen.

        Returns
        -------
        None

        """
        return self.configuration_register, f"{self.optical_alignment}"

    async def update_register(self, read_register):
        """Publish the register values of the modules.

        Returns
        -------
        None

        """
        await super().update_register(read_register)

    def __repr__(self):
        """Represent the register in prettier format."""
        return f"{self.name}:\n {self.wavelength_register}\n {self.configuration_register}\n"


class MiniOPG(interfaces.CanbusModule):
    """Implement the MiniOPG laser module.

    Attributes
    ----------
    name : `str`
        The name of the module.
    id : `int`
        The id of the module.
    error_code_register : `AsciiRegister`
        Corresponds to the "Error code" register.

    """

    def __init__(self, simulation_mode=False):
        super().__init__()
        self.name = "MiniOPG"
        self.id = 56
        self.error_code_register = AsciiRegister(
            module_name=self.name,
            module_id=self.id,
            register_name="Error Code",
        )

    async def update_register(self, read_register):
        """Publish the register values of the module.

        Returns
        -------
        None

        """
        await super().update_register(read_register)

    def __repr__(self):
        """Represent the register in prettier format."""
        return f"{self.name}:\n {self.error_code_register}\n"


class TK6(interfaces.CanbusModule):
    """Implement TK6 laser module which contains several temperature registers.

    Attributes
    ----------
    name : `str`
        The name of the module.
    id : `int`
        The id of the module.
    id_2 : `int`
        The second id of the module.
    display_temperature_register : `AsciiRegister`
        Handles the "Display temperature" register.
    set_temperature_register : `AsciiRegister`
        Handles the "Set temperature" register.
    display_temperature_register_2 : `AsciiRegister`
        Handles the "Display temperature" register.
    set_temperature_register_2 : `AsciiRegister`
        Handles the "Set temperature" register.

    """

    def __init__(self, simulation_mode=False):
        super().__init__()
        self.name = "TK6"
        self.id = 44
        self.id_2 = 45
        self.display_temperature_register = AsciiRegister(
            module_name=self.name,
            module_id=self.id,
            register_name="Display temperature",
        )
        self.set_temperature_register = AsciiRegister(
            module_name=self.name,
            module_id=self.id,
            register_name="Set temperature",
        )
        self.display_temperature_register_2 = AsciiRegister(
            module_name=self.name,
            module_id=self.id_2,
            register_name="Display temperature",
        )
        self.set_temperature_register_2 = AsciiRegister(
            module_name=self.name,
            module_id=self.id_2,
            register_name="Set temperature",
        )

    async def update_register(self, read_register):
        """Publish the register values of the module.

        Returns
        -------
        None

        """
        await super().update_register(read_register)

    def __repr__(self):
        """Represent the register in prettier format."""
        return (
            f"{self.name}:\n {self.display_temperature_register}\n {self.set_temperature_register}\n"
            f"{self.display_temperature_register_2}\n {self.set_temperature_register_2}\n"
        )


class HV40W(interfaces.CanbusModule):
    """Implement HV40W laser module which contains voltage register.

    Attributes
    ----------
    name : `str`
        The name of the module.
    id : `int`
        The id of the module.
    hv_voltage_register : `AsciiRegister`
        Handles the "HV Voltage" register.

    """

    def __init__(self, laser_id, simulation_mode=False):
        super().__init__()
        self.name = "HV40W"
        laser_ids = {1: 41, 2: 40}
        self.id = laser_ids[laser_id]
        self.hv_voltage_register = AsciiRegister(
            module_name=self.name,
            module_id=self.id,
            register_name="HV voltage",
        )

    async def update_register(self, read_register):
        """Publishes the register values of the module.

        Returns
        -------
        None

        """
        await super().update_register(read_register)

    def __repr__(self):
        """Represent the register in prettier format."""
        return f"{self.name}:\n {self.hv_voltage_register}\n"


class DelayLin(interfaces.CanbusModule):
    """Implement DelayLin laser module.

    Attributes
    ----------
    name : `str`
        The name of the module.
    id : `int`
        The id of the module.
    error_code_register : `AsciiRegister`
        Handles the "Error code" register.
    """

    def __init__(self, laser_id, simulation_mode=False):
        super().__init__()
        self.name = "DelayLin"
        laser_ids = {1: 40, 2: 47}
        self.id = laser_ids[laser_id]
        self.error_code_register = AsciiRegister(
            module_name=self.name,
            module_id=self.id,
            register_name="Error Code",
        )

    async def update_register(self, read_register):
        """Publish the register values of the module.

        Returns
        -------
        None

        """
        await super().update_register(read_register)

    def __repr__(self):
        """Represent the register in prettier format."""
        return f"{self.name}:\n {self.error_code_register}\n"


class LDCO48BP(interfaces.CanbusModule):
    """A hardware module for the laser.

    Attributes
    ----------
    name : `str`
        The name of the module.
    id : `int`
        The id of the module.
    id_2 : `int`
        The second id of the module.
    id_3 : `int`
        The third id of the module.
    display_temperature_register : `AsciiRegister`
        Handles the "Display temperature" register.
    display_temperature_register_2 : `AsciiRegister`
        Handles the "Display temperature" register.
    display_temperature_register_3 : `AsciiRegister`
        Handles the "Display temperature" register.

    """

    def __init__(self, laser_id, simulation_mode=False):
        super().__init__()
        self.name = "LDCO48BP"
        laser_ids = {
            1: [30, 29, 24, 24],
            2: [50, 48, 29, 28],
        }  # PF I really don't love this.

        self.id, self.id_2, self.id_3, self.id_4 = laser_ids[laser_id]

        self.display_temperature_register = AsciiRegister(
            module_name=self.name,
            module_id=self.id,
            register_name="Display temperature",
        )
        self.display_temperature_register_2 = AsciiRegister(
            module_name=self.name,
            module_id=self.id_2,
            register_name="Display temperature",
        )
        self.display_temperature_register_3 = AsciiRegister(
            module_name=self.name,
            module_id=self.id_3,
            register_name="Display temperature",
        )
        self.display_temperature_register_4 = AsciiRegister(
            module_name=self.name,
            module_id=self.id_4,
            register_name="Display temperature",
        )

    async def update_register(self, read_register):
        """Publish the register values of the module.

        Returns
        -------
        None
        """
        await super().update_register(read_register)

    def __repr__(self):
        """Represent the register in prettier format."""
        return (
            f"{self.name}:\n {self.display_temperature_register}\n"
            f"{self.display_temperature_register_2}\n {self.display_temperature_register_3}\n"
            f"{self.display_temperature_register_3}\n"
        )


class MLDCO48(interfaces.CanbusModule):
    """Implement MLDCO48 laser module which contains temperature registers.

    Attributes
    ----------
    name : `str`
        The name of the module.
    id : `int`
        The id of the module.
    id_2 : `int`
        The second id of the module.
    display_temperature_register : `AsciiRegister`
        Handles the "Display temperature" register.
    display_temperature_register_2 : `AsciiRegister`
        Handles the "Display temperature" register.
    """

    def __init__(self, simulation_mode=False):
        super().__init__()
        self.name = "M_LDCO48"
        self.id = 33
        self.id_2 = 34
        self.display_temperature_register = AsciiRegister(
            module_name=self.name,
            module_id=self.id,
            register_name="Display temperature",
        )
        self.display_temperature_register_2 = AsciiRegister(
            module_name=self.name,
            module_id=self.id_2,
            register_name="Display temperature",
        )

    async def update_register(self, read_register):
        """Publish the register values of the module.

        Returns
        -------
        None

        """
        await super().update_register(read_register)

    def __repr__(self):
        """Represent the register in prettier format."""
        return f"{self.name}:\n {self.display_temperature_register}\n {self.display_temperature_register_2}\n"


class E5DCB(interfaces.CompoWayFRegisterModule):
    """The Omron Temperature sensor for the laser.

    Attributes
    ----------
    name : `str`
        The name of the module.
    id : `int`
        The id of the module.
    set_point_register : `CompoWayFDataRegister`
        Corresponds to the set-point register.
    run_stop_register : `CompoWayFOperationRegister`
        Corresponds to the run/stop operation register.

    """

    def __init__(self, simulation_mode=False):
        super().__init__()
        self.name = "E5DCB"
        self.id_1 = 1
        self.set_point_register = CompoWayFDataRegister(
            module_name=self.name,
            module_id=self.id_1,
            register_name="Set Point",
            read_only=False,
            accepted_values=range(-200, 1000),
            simulation_mode=simulation_mode,
        )

        self.run_stop_register = CompoWayFOperationRegister(
            module_name=self.name,
            module_id=self.id_1,
            register_name="Run Stop",
            accepted_values=[0, 1, True, False],
            simulation_mode=simulation_mode,
        )

    async def update_register(self, read_register):
        """Publish the register values of the module.

        Returns
        -------
        None
        """
        await super().update_register(read_register)

    def __repr__(self):
        """Represent the register in prettier format."""
        return f"{self.name}:\n {self.run_stop_register}\n{self.set_point_register}\n"
