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
sometimes set.
Each class contains a method to update_register its registers' values.

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
]
import logging
from .ascii import AsciiRegister
from .enums import Power, Mode, Output, NoSCU, SCUConfiguration


class CPU8000:
    """A module for the laser.

    Parameters
    ----------
    commander : `TCPIPClient`
        A reference to the tcp/ip client.
    simulation_mode : `bool`, optional
        False for normal operation, true for simulation operation.

    Attributes
    ----------
    log : `logging.Logger`
        The log for the class.
    name : `str`
        Name of the module.
    id : `int`
        The ID of the module.
    commander : `TCPIPClient`
        A reference to the tcp/ip client.
    power_register : `AsciiRegister`
        Handles the "Power" register for this module.
    display_current_register : `AsciiRegister`
        Handles the "Display current" register.
    fault_register : `AsciiRegister`
        Handles the "Fault code" register.


    """

    def __init__(self, commander, simulation_mode=False):
        self.log = logging.getLogger("CPU8000")
        self.name = "CPU8000"
        self.id = 16
        self.commander = commander
        self.power_register = AsciiRegister(
            commander=commander,
            module_name=self.name,
            module_id=self.id,
            register_name="Power",
            simulation_mode=simulation_mode,
        )
        self.display_current_register = AsciiRegister(
            commander=commander,
            module_name=self.name,
            module_id=self.id,
            register_name="Display Current",
            simulation_mode=simulation_mode,
        )
        self.fault_register = AsciiRegister(
            commander=commander,
            module_name=self.name,
            module_id=self.id,
            register_name="Fault code",
            simulation_mode=simulation_mode,
        )
        self.log.debug(f"{self.name} Module initialized")

    async def update_register(self):
        """Publish the registers located inside of this module.

        Returns
        -------
        None

        """
        await self.power_register.read_register_value()
        await self.display_current_register.read_register_value()
        await self.fault_register.read_register_value()

    def __repr__(self):
        return f"CPU8000:\n {self.power_register}\n {self.display_current_register}\n {self.fault_register}\n"


class MCPU800:
    """A hardware module for the laser.

    Parameters
    ----------
    commander : `TCPIPClient`
        A reference to the tcp/ip client
    simulation_mode : `bool`
        False for normal operation, true for simulation operation.

    Attributes
    ----------
    name : `str`
        The name of the module.
    id : `int`
        The id of the module.
    id_2 : `int`
        The second id of the module.
    commander : `TCPIPClient`
        A reference to the TCP/IP client.
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

    def __init__(self, commander, simulation_mode=False):
        self.name = "M_CPU800"
        self.id = 17
        self.id_2 = 18
        self.commander = commander
        self.power_register = AsciiRegister(
            commander=commander,
            module_name=self.name,
            module_id=self.id,
            register_name="Power",
            simulation_mode=simulation_mode,
        )
        self.display_current_register = AsciiRegister(
            commander=commander,
            module_name=self.name,
            module_id=self.id,
            register_name="Display Current",
            simulation_mode=simulation_mode,
        )
        self.fault_register = AsciiRegister(
            commander=commander,
            module_name=self.name,
            module_id=self.id,
            register_name="Fault code",
            simulation_mode=simulation_mode,
        )

        self.power_register_2 = AsciiRegister(
            commander=commander,
            module_name=self.name,
            module_id=self.id_2,
            register_name="Power",
            read_only=False,
            accepted_values=list(Power),
            simulation_mode=simulation_mode,
        )
        self.display_current_register_2 = AsciiRegister(
            commander=commander,
            module_name=self.name,
            module_id=self.id_2,
            register_name="Display Current",
            simulation_mode=simulation_mode,
        )
        self.fault_register_2 = AsciiRegister(
            commander=commander,
            module_name=self.name,
            module_id=self.id_2,
            register_name="Fault code",
            simulation_mode=simulation_mode,
        )
        self.continous_burst_mode_trigger_burst_register = AsciiRegister(
            commander=commander,
            module_name=self.name,
            module_id=self.id_2,
            register_name="Continuous %2F Burst mode %2F Trigger burst",
            read_only=False,
            accepted_values=list(Mode),
            simulation_mode=simulation_mode,
        )
        self.output_energy_level_register = AsciiRegister(
            commander=commander,
            module_name=self.name,
            module_id=self.id_2,
            register_name="Output Energy level",
            read_only=False,
            accepted_values=list(Output),
            simulation_mode=simulation_mode,
        )
        self.frequency_divider_register = AsciiRegister(
            commander=commander,
            module_name=self.name,
            module_id=self.id_2,
            register_name="Frequency divider",
            read_only=False,
            accepted_values=range(1, 5001),
            simulation_mode=simulation_mode,
        )
        self.burst_pulse_left_register = AsciiRegister(
            commander=commander,
            module_name=self.name,
            module_id=self.id_2,
            register_name="Burst pulses to go",
            simulation_mode=simulation_mode,
        )
        self.qsw_adjustment_output_delay_register = AsciiRegister(
            commander=commander,
            module_name=self.name,
            module_id=self.id_2,
            register_name="QSW Adjustment output delay",
            simulation_mode=simulation_mode,
        )
        self.repetition_rate_register = AsciiRegister(
            commander=commander,
            module_name=self.name,
            module_id=self.id_2,
            register_name="Repetition rate",
            simulation_mode=simulation_mode,
        )
        self.synchronization_mode_register = AsciiRegister(
            commander=commander,
            module_name=self.name,
            module_id=self.id_2,
            register_name="Synchronization mode",
            simulation_mode=simulation_mode,
        )
        self.burst_length_register = AsciiRegister(
            commander=commander,
            module_name=self.name,
            module_id=self.id_2,
            register_name="Burst length",
            read_only=False,
            accepted_values=range(1, 50001),
            simulation_mode=simulation_mode,
        )

    async def start_propagating(self):
        """Start the propagation of the laser.

        If used while the laser is propagating, no discernable effect occurs.

        Returns
        -------
        None

        """
        await self.continous_burst_mode_trigger_burst_register.read_register_value()
        rv = self.continous_burst_mode_trigger_burst_register.register_value
        if rv in list(Mode):
            await self.power_register_2.set_register_value(Power.ON)
        else:
            raise RuntimeError(f"{rv} is not in one of accepted values")

    async def stop_propagating(self):
        """Stop the propagation of the laser.

        If used while the laser is not propagating, no discernable effect
        occurs.

        Returns
        -------
        None

        """
        await self.power_register_2.set_register_value(Power.OFF)

    async def set_output_energy_level(self, value):
        """Set the output energy level for the laser.

        Parameters
        ----------
        value : `str`, {OFF,Adjust,MAX}

        Returns
        -------
        None
        """
        await self.output_energy_level_register.set_register_value(value)

    async def set_propagation_mode(self, value):
        """Set the propagation mode of the laser.

        value : `str`, {Continuous, Burst, Trigger}
            The mode to be set
            Continuous: Continuous pulse
            Burst: Pulses a set number of times at regular interval
            Trigger: Trigger a pulse using an external device
            Trigger has not been used as we have no source.
        """
        await self.continous_burst_mode_trigger_burst_register.set_register_value(
            Mode(value)
        )

    async def set_burst_count(self, value):
        """Set the burst count for the laser when in burst mode.

        Parameters
        value : `int`
            The amount of pulses to perform.
            Accepts values between 1 and 50000
        """
        await self.burst_length_register.set_register_value(value)

    async def update_register(self):
        """Publish the register values of the module.

        Returns
        -------
        None

        """
        await self.power_register.read_register_value()
        await self.display_current_register.read_register_value()
        await self.fault_register.read_register_value()
        await self.power_register_2.read_register_value()
        await self.display_current_register_2.read_register_value()
        await self.fault_register_2.read_register_value()
        await self.continous_burst_mode_trigger_burst_register.read_register_value()
        await self.output_energy_level_register.read_register_value()
        await self.frequency_divider_register.read_register_value()
        await self.burst_pulse_left_register.read_register_value()
        await self.qsw_adjustment_output_delay_register.read_register_value()
        await self.repetition_rate_register.read_register_value()
        await self.synchronization_mode_register.read_register_value()
        await self.burst_length_register.read_register_value()

    def __repr__(self):
        return (
            f"M_CPU800:\n {self.power_register}\n {self.display_current_register}\n"
            f"{self.fault_register}\n {self.power_register_2}\n {self.display_current_register_2}\n"
            f"{self.fault_register_2}\n {self.continous_burst_mode_trigger_burst_register}\n"
            f"{self.output_energy_level_register}\n {self.frequency_divider_register}\n"
            f"{self.burst_pulse_left_register}\n {self.qsw_adjustment_output_delay_register}\n"
            f"{self.repetition_rate_register}\n {self.synchronization_mode_register}\n"
            f"{self.burst_length_register}\n"
        )


class LLPMKU:
    """A hardware module for the laser.

    Parameters
    ----------
    commander : `TCPIPClient`
        A reference to the tcp/ip client
    simulation_mode : `bool`
        False for normal operation, true for simulation operation.

    Attributes
    ----------
    name : `str`
        The name of the module.
    id : `int`
        The id of the module.
    commander : `TCPIPClient`
        A reference to the tcp/ip client.
    power_register : `AsciiRegister`
        Handles the "Power" register.

    """

    def __init__(self, commander, simulation_mode=False):
        self.name = "11PMKu"
        self.id = 54
        self.commander = commander
        self.power_register = AsciiRegister(
            commander=commander,
            module_name=self.name,
            module_id=self.id,
            register_name="Power",
            simulation_mode=simulation_mode,
        )

    async def update_register(self):
        """Publish the register values of the module.

        Returns
        -------
        None

        """
        await self.power_register.read_register_value()

    def __repr__(self):
        return f"11PMKu:\n {self.power_register}"


class MaxiOPG:
    """A hardware module for the laser.

    Parameters
    ----------
    commander : `TCPIPClient`
        A reference to the tcp/ip client
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
    commander : `TCPIPClient`
        A reference to the tcp/ip client.
    wavelength_register : `AsciiRegister`
        Handles the "WaveLength" register.
    configuration_register : `AsciiRegister`
        Handles the "Configuration" register.
    """

    def __init__(self, commander, simulation_mode=False, configuration=NoSCU.NO_SCU):
        self.name = "MaxiOPG"
        self.id = 31
        self.commander = commander
        self.configuration = configuration
        self.optical_alignment = "straight-through"
        self.wavelength_register = AsciiRegister(
            commander=commander,
            module_name=self.name,
            module_id=self.id,
            register_name="WaveLength",
            read_only=False,
            accepted_values=range(300, 1100),
            simulation_mode=simulation_mode,
        )
        if self.configuration == NoSCU.NO_SCU:
            self.configuration_register = AsciiRegister(
                commander=commander,
                module_name=self.name,
                module_id=self.id,
                register_name="Configuration",
                read_only=False,
                accepted_values=list(NoSCU),
                simulation_mode=simulation_mode,
            )
        elif self.configuration == SCUConfiguration.SCU:
            self.configuration_register = AsciiRegister(
                commander=commander,
                module_name=self.name,
                module_id=self.id,
                register_name="Configuration",
                read_only=False,
                accepted_values=list(SCUConfiguration),
                simulation_mode=simulation_mode,
            )
        else:
            raise ValueError("Invalid configuration value")

    async def change_wavelength(self, wavelength):
        """Change the wavelength of the laser.

        Parameters
        ----------
        wavelength : `float`

        Returns
        -------
        None

        """
        await self.wavelength_register.set_register_value(wavelength)

    async def set_configuration(self):
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
        if self.optical_alignment == "straight-through":
            await self.configuration_register.set_register_value(self.configuration)
        else:
            await self.configuration_register.set_register_value(
                f"{self.optical_alignment} {self.configuration}"
            )

    async def update_register(self):
        """Publish the register values of the modules.

        Returns
        -------
        None

        """
        await self.wavelength_register.read_register_value()
        await self.configuration_register.read_register_value()

    def __repr__(self):
        return f"{self.name}:\n {self.wavelength_register}\n {self.configuration_register}\n"


class MiniOPG:
    """A hardware module for the laser.

    Parameters
    ----------
    commander : `TCPIPClient`
        A reference to the tcp/ip client
    simulation_mode : `bool`
        False for normal operation, true for simulation operation.
    Attributes
    ----------
    name : `str`
        The name of the module.
    id : `int`
        The id of the module.
    commander : `TCPIPClient`
        A reference to the tcp/ip client.
    error_code_register : `AsciiRegister`
        Corresponds to the "Error code" register.

    """

    def __init__(self, commander, simulation_mode=False):
        self.name = "MiniOPG"
        self.id = 56
        self.commander = commander
        self.error_code_register = AsciiRegister(
            commander=commander,
            module_name=self.name,
            module_id=self.id,
            register_name="Error Code",
            simulation_mode=simulation_mode,
        )

    async def update_register(self):
        """Publish the register values of the module.

        Returns
        -------
        None

        """
        await self.error_code_register.read_register_value()

    def __repr__(self):
        return f"{self.name}:\n {self.error_code_register}\n"


class TK6:
    """A hardware module for the laser.

    Parameters
    ----------
    commander : `TCPIPClient`
        A reference to the tcp/ip client
    simulation_mode : `bool`
        False for normal operation, true for simulation operation.

    Attributes
    ----------
    name : `str`
        The name of the module.
    id : `int`
        The id of the module.
    id_2 : `int`
        The second id of the module.
    commander : `TCPIPClient`
        A reference to the tcp/ip client.
    display_temperature_register : `AsciiRegister`
        Handles the "Display temperature" register.
    set_temperature_register : `AsciiRegister`
        Handles the "Set temperature" register.
    display_temperature_register_2 : `AsciiRegister`
        Handles the "Display temperature" register.
    set_temperature_register_2 : `AsciiRegister`
        Handles the "Set temperature" register.

    """

    def __init__(self, commander, simulation_mode=False):
        self.name = "TK6"
        self.id = 44
        self.id_2 = 45
        self.commander = commander
        self.display_temperature_register = AsciiRegister(
            commander=commander,
            module_name=self.name,
            module_id=self.id,
            register_name="Display temperature",
            simulation_mode=simulation_mode,
        )
        self.set_temperature_register = AsciiRegister(
            commander=commander,
            module_name=self.name,
            module_id=self.id,
            register_name="Set temperature",
            simulation_mode=simulation_mode,
        )
        self.display_temperature_register_2 = AsciiRegister(
            commander=commander,
            module_name=self.name,
            module_id=self.id_2,
            register_name="Display temperature",
            simulation_mode=simulation_mode,
        )
        self.set_temperature_register_2 = AsciiRegister(
            commander=commander,
            module_name=self.name,
            module_id=self.id_2,
            register_name="Set temperature",
            simulation_mode=simulation_mode,
        )

    async def update_register(self):
        """Publish the register values of the module.

        Returns
        -------
        None

        """
        await self.display_temperature_register.read_register_value()
        await self.set_temperature_register.read_register_value()
        await self.display_temperature_register_2.read_register_value()
        await self.set_temperature_register_2.read_register_value()

    def __repr__(self):
        return (
            f"{self.name}:\n {self.display_temperature_register}\n {self.set_temperature_register}\n"
            f"{self.display_temperature_register_2}\n {self.set_temperature_register_2}\n"
        )


class HV40W:
    """A hardware module for the laser.

    Parameters
    ----------
    commander : `TCPIPClient`
        A reference to the tcp/ip client
    simulation_mode : `bool`
        False for normal operation, true for simulation operation.

    Attributes
    ----------
    name : `str`
        The name of the module.
    id : `int`
        The id of the module.
    commander : `TCPIPClient`
        A reference to the tcp/ip client.
    hv_voltage_register : `AsciiRegister`
        Handles the "HV Voltage" register.

    """

    def __init__(self, commander, simulation_mode=False):
        self.name = "HV40W"
        self.id = 41
        self.commander = commander
        self.hv_voltage_register = AsciiRegister(
            commander=commander,
            module_name=self.name,
            module_id=self.id,
            register_name="HV voltage",
            simulation_mode=simulation_mode,
        )

    async def update_register(self):
        """Publishes the register values of the module.

        Returns
        -------
        None

        """
        await self.hv_voltage_register.read_register_value()

    def __repr__(self):
        return f"{self.name}:\n {self.hv_voltage_register}\n"


class DelayLin:
    """A hardware module for the laser.

    Parameters
    ----------
    commander : `TCPIPClient`
        A reference to the tcp/ip client
    simulation_mode : `bool`
        False for normal operation, true for simulation operation.

    Attributes
    ----------
    name : `str`
        The name of the module.
    id : `int`
        The id of the module.
    commander : `TCPIPClient`
        A reference to the tcp/ip client.
    error_code_register : `AsciiRegister`
        Handles the "Error code" register.
    """

    def __init__(self, commander, simulation_mode=False):
        self.name = "DelayLin"
        self.id = 40
        self.commander = commander
        self.error_code_register = AsciiRegister(
            commander=commander,
            module_name=self.name,
            module_id=self.id,
            register_name="Error Code",
            simulation_mode=simulation_mode,
        )

    async def update_register(self):
        """Publish the register values of the module.

        Returns
        -------
        None

        """
        await self.error_code_register.read_register_value()

    def __repr__(self):
        return f"{self.name}:\n {self.error_code_register}\n"


class LDCO48BP:
    """A hardware module for the laser.

    Parameters
    ----------
    commander : `TCPIPClient`
        A reference to the tcp/ip client
    simulation_mode : `bool`
        False for normal operation, true for simulation operation.
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
    commander : `TCPIPClient`
        A reference to the tcp/ip client.
    display_temperature_register : `AsciiRegister`
        Handles the "Display temperature" register.
    display_temperature_register_2 : `AsciiRegister`
        Handles the "Display temperature" register.
    display_temperature_register_3 : `AsciiRegister`
        Handles the "Display temperature" register.

    """

    def __init__(self, commander, simulation_mode=False):
        self.name = "LDCO48BP"
        self.id = 30
        self.id_2 = 29
        self.id_3 = 24
        self.commander = commander
        self.display_temperature_register = AsciiRegister(
            commander=commander,
            module_name=self.name,
            module_id=self.id,
            register_name="Display temperature",
            simulation_mode=simulation_mode,
        )
        self.display_temperature_register_2 = AsciiRegister(
            commander=commander,
            module_name=self.name,
            module_id=self.id_2,
            register_name="Display temperature",
            simulation_mode=simulation_mode,
        )
        self.display_temperature_register_3 = AsciiRegister(
            commander=commander,
            module_name=self.name,
            module_id=self.id_3,
            register_name="Display temperature",
            simulation_mode=simulation_mode,
        )

    async def update_register(self):
        """Publish the register values of the module.

        Returns
        -------
        None
        """
        await self.display_temperature_register.read_register_value()
        await self.display_temperature_register_2.read_register_value()
        await self.display_temperature_register_3.read_register_value()

    def __repr__(self):
        return (
            f"{self.name}:\n {self.display_temperature_register}\n"
            f"{self.display_temperature_register_2}\n {self.display_temperature_register_3}\n"
        )


class MLDCO48:
    """A hardware module for the laser.

    Parameters
    ----------
    commander : `TCPIPClient`
        A reference to the tcp/ip client
    simulation_mode : `bool`
        False for normal operation, true for simulation operation.

    Attributes
    ----------
    name : `str`
        The name of the module.
    id : `int`
        The id of the module.
    id_2 : `int`
        The second id of the module.
    commander : `TCPIPClient`
        A reference to the tcp/ip client.
    display_temperature_register : `AsciiRegister`
        Handles the "Display temperature" register.
    display_temperature_register_2 : `AsciiRegister`
        Handles the "Display temperature" register.
    """

    def __init__(self, commander, simulation_mode=False):
        self.name = "M_LDCO48"
        self.id = 33
        self.id_2 = 34
        self.commander = commander
        self.display_temperature_register = AsciiRegister(
            commander=commander,
            module_name=self.name,
            module_id=self.id,
            register_name="Display temperature",
            simulation_mode=simulation_mode,
        )
        self.display_temperature_register_2 = AsciiRegister(
            commander=commander,
            module_name=self.name,
            module_id=self.id_2,
            register_name="Display temperature",
            simulation_mode=simulation_mode,
        )

    async def update_register(self):
        """Publish the register values of the module.

        Returns
        -------
        None

        """
        await self.display_temperature_register.read_register_value()
        await self.display_temperature_register_2.read_register_value()

    def __repr__(self):
        return f"{self.name}:\n {self.display_temperature_register}\n {self.display_temperature_register_2}\n"
