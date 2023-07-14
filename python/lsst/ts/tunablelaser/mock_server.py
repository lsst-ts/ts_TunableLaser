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

__all__ = ["MockServer", "MockMessage", "MockNT900"]

import logging
import inspect
import asyncio

from lsst.ts import tcpip

from .enums import Power, Mode, Output, SCUConfiguration, NoSCU

TERMINATOR = "\r\n\x03"


class MockServer(tcpip.OneClientServer):
    """Simulates the TunableLaser.

    Parameters
    ----------
    port : `int`, optional
        The port that the server will start on.
    """

    def __init__(self, port=0) -> None:
        self.device = MockNT900()
        self.log = logging.getLogger(__name__)
        self.read_loop_task = asyncio.Future()
        super().__init__(
            name="TunableLaser Mock Server",
            host=tcpip.LOCAL_HOST,
            port=port,
            log=self.log,
            connect_callback=self.connect_callback,
        )

    def connect_callback(self, server):
        """Call when the client connects.

        Starts the command loop for the simulator.

        Parameters
        ----------
        server : `lsst.ts.tcpip.OneClientServer`
        """
        self.read_loop_task.cancel()
        if server.connected:
            self.read_loop_task = asyncio.create_task(self.cmd_loop())

    async def cmd_loop(self):
        """Return reply based on messaged received."""
        while self.connected:
            self.log.debug("inside cmd_loop")
            reply = await self.reader.readuntil(b"\r")
            if not reply:
                self.writer.close()
                return
            reply = self.device.parse_message(reply)
            reply += TERMINATOR
            self.log.debug(f"reply={reply.encode('ascii')}")
            self.writer.write(reply.encode("ascii"))
            await self.writer.drain()


class MockMessage:
    """Parse a command from the client.

    Parameters
    ----------
    msg : `bytes`
        The bytes received from the client.

    Raises
    ------
    `Exception`
        Raised when a message is malformed.
    """

    def __init__(self, msg):
        msg = msg.decode("ascii").strip(TERMINATOR)
        split_msg = msg.split("/")
        if len(split_msg) == 4:
            self.register_name = split_msg[1]
            self.register_id = split_msg[2]
            self.register_field = split_msg[3].lower()
            split_register_field = self.register_field.split(" ")
            self.register_field = "_".join(split_register_field)
        elif len(split_msg) == 5:
            self.register_name = split_msg[1]
            self.register_id = split_msg[2]
            self.register_field = split_msg[3].lower()
            split_register_field = self.register_field.split(" ")
            self.register_field = "_".join(split_register_field)
            self.register_parameter = split_msg[4]
        else:
            raise Exception("Message malformed")

    def __repr__(self):
        return f"{self.register_name}\n{self.register_id}\n{self.register_field}\n"


class MockNT900:
    """Implements a mock NT900 laser.

    Attributes
    ----------
    wavelength : `float`
        The wavelength of the laser.
    temperature : `float`
        The temperature of the laser.
    current : `str`
        The electrical current of the laser.
    propagating : `str`
        Whether the laser is propagating.
    output_energy_level : `str`
        The energy level of the laser's output
    configuration : `str`
        Which output the laser is propagating from.
    log : `logging.Logger`
        The log for this class.
    """

    def __init__(self):
        self.scu = False
        self.wavelength = 650
        self.temperature = 19
        self.cpu8000_current = "19A"
        self.m_cpu800_current = "19A"
        self.cpu8000_power = Power.ON.value
        self.m_cpu800_power = Power.ON.value
        self.propagating = Power.OFF.value
        self.output_energy_level = Output.OFF.value
        if not self.scu:
            self.configuration = NoSCU.NO_SCU.value
        else:
            self.configuration = SCUConfiguration.SCU.value
        self.propagation_mode = Mode.CONTINUOUS.value
        self.burst_length = 1
        self.log = logging.getLogger(__name__)
        self.log.debug("MockNT900 initialized")

    def check_limits(self, value, min, max):
        """Check the limits of a value.

        Parameters
        ----------
        value : `int`
            The value to check.
        min : `int`
            The minimum value.
        max : `int`
            The max value

        Returns
        -------
        reply : `str`
            if too low: return error
            if too high: return error
            if successful: return empty message
        """
        if int(value) < min:
            reply = "'''Error: (12) Violating bottom value limit"
            return reply
        if int(value) > max:
            reply = "'''Error: (11) Violating top value limit"
            return reply
        else:
            reply = ""
            return reply

    def parse_message(self, msg):
        """Parse and return the result of the message.

        Parameters
        ----------
        msg : `bytes`
            The message to parse.

        Returns
        -------
        reply : `bytes`
            The reply of the command parsed.
        """
        try:
            self.log.info(msg)
            split_msg = MockMessage(msg)
            self.log.debug(split_msg)
            command_name = "_".join(
                (
                    split_msg.register_name.lower(),
                    split_msg.register_id,
                    split_msg.register_field,
                )
            )
            self.log.debug(f"{command_name=}")
            if not hasattr(split_msg, "register_parameter"):
                parameter = None
            else:
                parameter = split_msg.register_parameter
                command_name = "set_" + command_name
            self.log.debug(f"{parameter=}")
            command_name = "do_" + command_name
            self.log.debug(f"{command_name=}")
            methods = inspect.getmembers(self, inspect.ismethod)
            for name, func in methods:
                if name == command_name:
                    self.log.debug(command_name)
                    if parameter is None:
                        reply = func()
                    else:
                        reply = func(parameter)
                    self.log.debug(f"reply: {reply}")
                    return reply
                elif (
                    command_name
                    == "do_m_cpu800_18_continuous_%2f_burst_mode_%2f_trigger_burst"
                ):
                    reply = self.do_m_cpu800_18_continuous_burst_mode_trigger_burst()
                    self.log.debug(f"reply: {reply}")
                    return reply
                elif (
                    command_name
                    == "do_set_m_cpu800_18_continuous_%2f_burst_mode_%2f_trigger_burst"
                ):
                    reply = self.do_set_m_cpu800_18_continuous_burst_mode_trigger_burst(
                        parameter
                    )
                    self.log.debug(f"reply: {reply}")
                    return reply
            self.log.error(f"command {command_name} not implemented")
            return "NA"
        except Exception:
            self.log.exception("Unexpected exception occurred.")
            raise
        finally:
            pass

    def do_maxiopg_31_wavelength(self):
        """Return current wavelength as formatted string.

        Returns
        -------
        `str`
            The current wavelength.
        """
        return f"{self.wavelength}nm"

    def do_set_maxiopg_31_wavelength(self, wavelength):
        """Set wavelength.

        Parameters
        ----------
        wavelength : `str`
            The wavelength to set, must be between 300 and 1100 nanometers.

        Returns
        -------
        reply : `str`
            Successful reply: empty message
            Error: starts with ''' plus error message
        """
        reply = self.check_limits(wavelength, 300, 1100)
        if not reply.startswith("'''"):
            self.wavelength = wavelength
        return reply

    def do_cpu8000_16_power(self):
        """Return the power state of the module

        Returns
        -------
        `str`
            The current power state of the module.
        """
        return f"{self.cpu8000_power}"

    def do_m_cpu800_17_power(self):
        """Return the power state of the module

        Returns
        -------
        `str`
            The current power state of the module
        """
        return f"{self.m_cpu800_power}"

    def do_m_cpu800_17_fault_code(self):
        """Return the fault code of the module

        Returns
        -------
        `str`
            The current fault code.
            Always returns 0.
        """
        return "0"

    def do_m_cpu800_17_display_current(self):
        """Return the power current of the module

        Returns
        -------
        `str`
            The displayed current.
        """
        return f"{self.m_cpu800_current}"

    def do_set_m_cpu800_18_power(self, state):
        """Set the propagation state of the laser.

        Parameters
        ----------
        state : `str`, {OFF, ON, FAULT}
            The propagation state

            * OFF: Laser is not propagating
            * ON: Laser is propagating
            * FAULT: Laser is in fault, usually interlock is engaged

        Returns
        -------
        `str`
            An empty message
        """
        try:
            self.propagating = Power(state).value
            return ""
        except ValueError:
            self.log.error(f"{state} not in {list(Power)}")
            return "'''Error: (13) Wrong value, not included in allowed values list"

    def do_m_cpu800_18_power(self):
        """Return propagation state.

        Returns
        -------
        `str`
        """
        return f"{self.propagating}"

    def do_m_cpu800_18_fault_code(self):
        """Return the fault code of the module."""
        return "0"

    def do_m_cpu800_18_display_current(self):
        """Return the power current of the module."""
        return f"{self.m_cpu800_current}"

    def do_cpu8000_16_display_current(self):
        """Return current as formatted string.

        Returns
        -------
        `str`
        """
        return f"{self.cpu8000_current}"

    def do_cpu8000_16_fault_code(self):
        """Return fault code of the module.

        Returns
        -------
        `str`
        """
        return "0"

    def do_m_cpu800_18_continuous_burst_mode_trigger_burst(self):
        """Return laser propagation mode.

        Returns
        -------
        `str`
        """
        return f"{self.propagation_mode}"

    def do_set_m_cpu800_18_continuous_burst_mode_trigger_burst(self, mode):
        """Set the propagation mode of the laser.

        Parameters
        ----------
        mode : `str`, {Continuous, Burst, Trigger}
            The mode to be set.

        Returns
        -------
        `str`
            An empty message if successful or an error message
            if mode not in accepted values.
        """
        try:
            self.propagation_mode = Mode(mode).value
            return ""
        except ValueError:
            self.log.error(f"{mode} not in {list(Mode)}")
            return "'''Error: (13) Wrong value, not included in allowed values list"

    def do_m_cpu800_18_output_energy_level(self):
        """Return current output energy level as formatted string.

        Returns
        -------
        `str`
        """
        return f"{self.output_energy_level}"

    def do_set_m_cpu800_18_output_energy_level(self, energy_level):
        """Change output energy level as formatted string.

        Returns
        -------
        `str`
        """
        self.output_energy_level = energy_level
        return ""

    def do_m_cpu800_18_frequency_divider(self):
        """Return current frequency divider as formatted string.

        Returns
        -------
        `str`
        """
        return "0"

    def do_m_cpu800_18_burst_pulses_to_go(self):
        """Return current burst pulses left as formatted string.

        Returns
        -------
        `str`
        """
        return "0"

    def do_m_cpu800_18_qsw_adjustment_output_delay(self):
        """Return current qsw adjustment output delay as formatted string.

        Returns
        -------
        `str`
        """
        return "0"

    def do_m_cpu800_18_repetition_rate(self):
        """Return current repetition rate as formatted string.

        Returns
        -------
        `str`
        """
        return "1"

    def do_m_cpu800_18_synchronization_mode(self):
        """Return current synchronization mode as formatted string.

        Returns
        -------
        `str`
        """
        return "0"

    def do_m_cpu800_18_burst_length(self):
        """Return current burst length as formatted string.

        Returns
        -------
        `str`
        """
        return f"{self.burst_length}"

    def do_set_m_cpu800_18_burst_length(self, count):
        self.burst_length = count
        return ""

    def do_11pmku_54_power(self):
        return "19A"

    def do_maxiopg_31_configuration(self):
        """Return current configuration as formatted string.

        Returns
        -------
        `str`
        """
        return f"{self.configuration}"

    def do_set_maxiopg_31_configuration(self, configuration):
        """Change the configuration as formatted string.

        Returns
        -------
        `str`
        """
        if not self.scu:
            self.configuration = NoSCU(configuration)
            return ""
        else:
            self.configuration = SCUConfiguration(configuration)
            return ""

    def do_miniopg_56_error_code(self):
        """Return current error code as formatted string.

        Returns
        -------
        `str`
        """
        return "0"

    def do_tk6_44_display_temperature(self):
        return f"{self.temperature}"

    def do_tk6_45_display_temperature(self):
        return f"{self.temperature}"

    def do_set_temperature(self):
        """Change setpoint temperature as formatted string.

        Returns
        -------
        `str`
        """
        return f"{self.temperature}C"

    def do_hv40w_41_hv_voltage(self):
        """Return current hv voltage as formatted string.

        Returns
        -------
        `str`
        """
        return "10"

    def do_delaylin_40_error_code(self):
        """Return error code from module"""
        return "0"

    def do_ldco48bp_30_display_temperature(self):
        """Return temperature from module"""
        return f"{self.temperature}"

    def do_ldco48bp_29_display_temperature(self):
        """Return temperature from module"""
        return f"{self.temperature}"

    def do_ldco48bp_24_display_temperature(self):
        """Return temperature from module"""
        return f"{self.temperature}"

    def do_m_ldco48_33_display_temperature(self):
        """Return temperature from module"""
        return f"{self.temperature}"

    def do_m_ldco48_34_display_temperature(self):
        """Return temperature from module"""
        return f"{self.temperature}"
