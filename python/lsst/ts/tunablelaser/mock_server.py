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

__all__ = [
    "StubbsLaserServer",
    "MainLaserServer",
    "MockNT252",
    "MockMessage",
    "MockNT900",
    "TempCtrlServer",
    "MockNP5450",
]

import asyncio
import inspect
import io
import logging
import random
from ipaddress import ip_address

from lsst.ts import tcpip

from .compoway_register import CompoWayFGeneralRegister
from .enums import Mode, NoSCU, Output, Power, SCUConfiguration

TERMINATOR = b"\r\n\x03"


class StubbsLaserServer(tcpip.OneClientReadLoopServer):
    """Implement Stubbs mock server.

    Attributes
    ----------
    device : `MockNT252`
        The mock NT252 device.
    """

    def __init__(self) -> None:
        self.device = MockNT252()
        super().__init__(
            port=0,
            host=tcpip.LOCAL_HOST,
            log=logging.getLogger(__name__),
            name="Stubbs Mock Laser",
            encoding="ascii",
            terminator=TERMINATOR,
        )

    async def read_and_dispatch(self):
        reply = await self.readuntil(b"\r")
        reply = reply.strip(self.terminator).decode(self.encoding)
        reply = self.device.parse_command(reply)
        await self.write_str(reply)


class MainLaserServer(tcpip.OneClientReadLoopServer):
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
            terminator=TERMINATOR,
            encoding="ascii",
        )

    async def read_and_dispatch(self):
        """Return reply based on messaged received."""
        reply = await self.readuntil(b"\r")
        reply = reply.strip(self.terminator).decode(self.encoding)
        reply = self.device.parse_message(reply)
        await self.write_str(reply)


class TempCtrlServer(tcpip.OneClientReadLoopServer):
    """Simulates the tcpip server for the temp ctrl.

    Parameters
    ----------
    port : `int`, optional
        The port that the server will start on.
    """

    def __init__(self, host=tcpip.LOCAL_HOST, port=0) -> None:
        self.device = MockNP5450()
        self.log = logging.getLogger(__name__)
        self.read_loop_task = asyncio.Future()
        try:
            ip_address(host)
            super().__init__(
                name="TempCtrl Mock Server",
                host=host,
                port=port,
                log=self.log,
                terminator=b"\r",
                encoding="ascii",
            )
        except ValueError:
            self.log.error(
                f"TempCtrlServer hostname was invalid, assuming temp ctrler unconnected: {host}"
            )
            super().__init__(
                name="TempCtrl Mock Server",
                host=tcpip.LOCAL_HOST,
                port=25,
                log=self.log,
                terminator=b"\r",
                encoding="ascii",
            )
            self.device = None

    async def read_and_dispatch(self):
        if self.device is not None:
            """Return reply based on messaged received."""
            reply = await self.readuntil(b"\r")
            reply = reply.strip(self.terminator)
            reply = self.device.parse_message(reply)
            await self.write_str(reply)
        else:
            await self.write_str("TempCtrler Unconnected")


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


class MockCompoWayFMessage:
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
        self.log = logging.getLogger(__name__)
        try:
            with io.BytesIO(msg) as f:
                stx = f.read(1).decode()
                if stx != "\x02":
                    self.log.error(f"expected STX of 0x2, but got: {stx}")

                self.node = f.read(2).decode()
                self.log.info(f"got node: {self.node}")

                subadd = f.read(2).decode()
                if subadd != "\x30\x30":
                    self.log.error(f"expected subadd of 00, but got: {subadd}")

                SID = f.read(1).decode()
                if SID != "\x30":
                    self.log.error(f"Expected SID of 0, but got: {SID}")

                self.MRC = f.read(2).decode()
                self.SRC = f.read(2).decode()

                # bytesio doesn't include a readuntil
                # the cmdtxt can be variable length, demarked by ETX byte
                # This read_elements setting only reads 1 word (4 bytes)
                # If this needs to be configurable in the future one way
                # is to make a dictionary like its done for register add
                # Doing range 64 for comfort, should only be 4 + 1 for ETX
                self.cmd_txt = ""
                for _ in range(64):
                    byte = f.read(1).decode()
                    # ETX byte
                    if byte == "\x03":
                        break
                    else:
                        self.cmd_txt = self.cmd_txt + byte

                self.log.info(f"got cmdframe: {self.cmd_txt}")

                bcc_frame = (
                    self.node
                    + subadd
                    + SID
                    + self.MRC
                    + self.SRC
                    + self.cmd_txt
                    + "\x03"
                )

                bcc_maker = CompoWayFGeneralRegister()
                expected_bcc = bcc_maker.generate_bcc(frame=bcc_frame)

                self.bcc = f.read(1).decode()
                if expected_bcc is not self.bcc:
                    raise ValueError(
                        f"Mismatch of BCC, got: {self.bcc}, expected: {expected_bcc}"
                    )

                # some type of read/write variable address cmd
                if self.MRC == "\x30\x31" and (
                    self.SRC == "\x30\x31" or self.SRC == "\x30\x32"
                ):
                    self.var_type = self.cmd_txt[:2]
                    self.address = self.cmd_txt[2:6]
                    bit_pos = self.cmd_txt[6:8]
                    if bit_pos != "\x30\x30":
                        self.log.error(
                            f"got incorrect bitposition, expected 00, got: {bit_pos}"
                        )
                    self.num_of_elements = self.cmd_txt[8:12]

                    if self.SRC == "\x30\x32":
                        self.write_data = self.cmd_txt[12:]
                elif (
                    self.MRC == "\x33\x30" and self.SRC == "\x30\x35"
                ):  # 30 05 operation reg
                    self.command_code = self.cmd_txt[:2]
                    self.related_info = self.cmd_txt[2:4]
                else:
                    raise ValueError(
                        f"Command not supported, got MRC {self.MRC} SRC {self.SRC}"
                    )
        except Exception as e:
            self.log.error(f"Message format not as expected. Message: {e}")
            raise Exception("Message malformed")

    def __repr__(self):
        return f"{self.node}\n{self.MRC}\n{self.SRC}\n{self.cmd_txt}\n{self.bcc}"


class MockNP5450:
    """Implements a mock NP5450 .

    Attributes
    ----------
    temperature : `float`
        The temperature of the laser.
    log : `logging.Logger`
        The log for this class.
    """

    def __init__(self):
        self.e5dcb_setpoint_temperature = random.randrange(1, 100)
        self.run_stop = False
        self.log = logging.getLogger(__name__)
        self.log.debug("NP5450 initialized")

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
            split_msg = MockCompoWayFMessage(msg)
            self.log.debug(split_msg)

            command_name = "do_"
            parameter = None

            if split_msg.MRC == "\x30\x31":
                if int(split_msg.num_of_elements) != 1:
                    raise ValueError(
                        "More than 1 number of element read/write not supported"
                    )

                if split_msg.SRC == "\x30\x31":
                    command_name += "get_"
                elif split_msg.SRC == "\x30\x32":
                    parameter = split_msg.write_data
                    command_name += "set_"

                command_name += str(split_msg.node) + "_"

                if split_msg.var_type == "\x38\x31":
                    # set point
                    if split_msg.address == "\x30\x30\x30\x33":
                        command_name += "sp"
            elif split_msg.MRC == "\x33\x30":
                # operation msg
                if split_msg.SRC == "\x30\x35":
                    command_name += "set_op_"

                command_name += str(split_msg.node) + "_"

                if split_msg.command_code == "\x30\x31":
                    command_name += "runstop"
                    parameter = split_msg.related_info

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
            self.log.error(f"command {command_name} not implemented")
            return "NA"
        except Exception as e:
            self.log.exception(f"Unexpected exception occurred: {e}.")
            raise
        finally:
            pass

    def do_set_01_sp(self, data):
        self.e5dcb_setpoint_temperature = data
        returnmsg = "\x30\x31" + "\x30\x30"  # node and subaddress
        returnmsg += "\x30\x30"  # end code
        returnmsg += "\x30\x31\x30\x32"  # mrc/src
        returnmsg += "\x30\x30\x30\x30"  # response code
        returnmsg += "\x03"  # ETX
        bcc_maker = CompoWayFGeneralRegister()
        bcc = bcc_maker.generate_bcc(frame=returnmsg)
        returnmsg = "\x02" + returnmsg + bcc
        return returnmsg

    def do_get_01_sp(self):
        returnmsg = "\x30\x31" + "\x30\x30"
        returnmsg += "\x30\x30"  # end code
        returnmsg += "\x30\x31\x30\x31"  # mrc/src
        returnmsg += "\x30\x30\x30\x30"  # response code
        returnmsg += str(self.e5dcb_setpoint_temperature)
        returnmsg += "\x03"  # ETX
        bcc_maker = CompoWayFGeneralRegister()
        bcc = bcc_maker.generate_bcc(frame=returnmsg)
        returnmsg = "\x02" + returnmsg + bcc
        return returnmsg

    def do_set_op_01_runstop(self, data):
        run_stop_related_info = {
            True: "\x30\x30",  # on
            False: "\x30\x31",  # off
            0: "\x30\x31",  # off
            1: "\x30\x30",  # on
        }
        if data in run_stop_related_info:
            self.run_stop = bool(run_stop_related_info[data])
        else:
            self.log.error(f"received bad data in related info: {data}")

        returnmsg = "\x30\x31" + "\x30\x30"
        returnmsg += "\x30\x30"  # end code
        returnmsg += "\x33\x30\x30\x35"  # mrc/src
        returnmsg += "\x30\x30\x30\x30"  # response code
        returnmsg += "\x03"  # ETX
        bcc_maker = CompoWayFGeneralRegister()
        bcc = bcc_maker.generate_bcc(frame=returnmsg)
        returnmsg = "\x02" + returnmsg + bcc
        return returnmsg

    def do_set_temperature(self):
        """Change setpoint temperature as formatted string.

        Returns
        -------
        `str`
        """
        return f"{self.temperature}C"


class MockNT252:
    """Implement the mock NT252 device.

    Attributes
    ----------
    log : `logging.Logger`
        The log.
    wavelength : `int`
        The wavelength.
    temperature : `int`
        The temperature.
    propagating : `Power`
        The propagation state of the laser.
    propagation_mode : `Mode`
        The propagation mode.
    output : `Output`
        The output energy level.
    display_current : `int`
        The display current.
    burst_length : `int`
        The burst length.
    """

    def __init__(self) -> None:
        self.log = logging.getLogger(__name__)
        self.wavelength = random.randrange(1, 1100)
        self.temperature = random.randrange(19, 21)
        self.propagating = Power.OFF
        self.propagation_mode = Mode.CONTINUOUS
        self.output = Output.OFF
        self.display_current = random.randrange(19, 21)
        self.burst_length = 0
        self.log.debug("MockNT252 initialized")

    def parse_command(self, msg):
        """Parse the message received and return response.

        Parameters
        ----------
        msg : `str`
            The message.
        """
        split_msg = MockMessage(msg)
        command_name = "do_" + split_msg.register_field
        self.log.debug(f"{command_name=}")
        try:
            command = getattr(self, command_name)
        except Exception:
            if command_name == "do_continuous_%2f_burst_mode_%2f_trigger_burst":
                command = getattr(self, "do_continuous_burst_mode_trigger_burst")
            else:
                raise NotImplementedError(f"{command_name} is not implemented")
        try:
            parameter = split_msg.register_parameter
        except Exception:
            parameter = None
        if parameter:
            try:
                response = command(parameter)
            except Exception:
                raise NotImplementedError(f"{command} needs to implement parameter.")
        else:
            response = command()
        return response

    def do_power(self, parameter=None):
        """Return or set the power status."""
        if parameter is not None:
            self.propagating = Power(parameter)
            return ""
        return self.propagating

    def do_display_temperature(self):
        """Return display temperature."""
        return f"{self.temperature} C"

    def do_set_temperature(self):
        """Return set temperature."""
        return f"{self.temperature} C"

    def do_wavelength(self, parameter=None):
        """Return or set wavelength."""
        if parameter is not None:
            self.wavelength = parameter
            return ""
        return f"{self.wavelength} nm"

    def do_display_current(self):
        """Return the display current."""
        return f"{self.display_current} A"

    def do_fault_code(self):
        """Return the fault code."""
        return "0"

    def do_continuous_burst_mode_trigger_burst(self, parameter=None):
        """Return or set the propagation mode."""
        if parameter is not None:
            self.propagation_mode = Mode(parameter)
            return ""
        return f"{self.propagation_mode}"

    def do_output_energy_level(self, parameter=None):
        """Return or set the output energy level."""
        if parameter is not None:
            self.output = Output(parameter)
            return ""
        else:
            return self.output

    def do_frequency_divider(self):
        """Return frequency divider."""
        return "0"

    def do_burst_pulses_to_go(self):
        """Return burst pulses to go."""
        return "0"

    def do_qsw_adjustment_output_delay(self):
        """Return qsw adjustment output delay."""
        return "0"

    def do_repetition_rate(self):
        """Return the repetition rate."""
        return "0"

    def do_synchronization_mode(self):
        """Return synchronization mode."""
        return "0"

    def do_burst_length(self, parameter=None):
        """Return or set the burst length."""
        if parameter is not None:
            self.burst_length = parameter
            return ""
        return f"{self.burst_length}"

    def do_hv_voltage(self):
        """Return hv voltage."""
        return "0"

    def do_error_code(self):
        """Return the error code."""
        return "0"

    def do_midiopg_31_wavelength(self):
        """Return current wavelength as formatted string.

        Returns
        -------
        `str`
            The current wavelength.
        """
        return f"{self.wavelength}nm"

    def do_set_midiopg_31_wavelength(self, wavelength):
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

    def do_tk6_44_display_temperature(self):
        return f"{self.temperature}"

    def do_tk6_45_display_temperature(self):
        return f"{self.temperature}"


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
        self.wavelength = random.randrange(1, 1100)
        self.temperature = random.randrange(19, 21)
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
