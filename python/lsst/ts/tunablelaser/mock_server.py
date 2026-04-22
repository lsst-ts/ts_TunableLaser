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
import re
from ipaddress import ip_address

from lsst.ts import tcpip, utils

from .compoway_register import CompoWayFGeneralRegister
from .enums import Mode, OpticalConfiguration, Output, Power

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
        reply = self.device.parse_message(reply)
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
        self.simulate_connection_unstability = False
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
        if self.simulate_connection_unstability:
            unstable = random.choices([True, False], [0.3, 0.7])
        else:
            unstable = [False]
        reply = await self.readuntil(b"\r")
        reply = reply.strip(self.terminator).decode(self.encoding)
        reply = self.device.parse_message(reply)
        if not unstable[0]:
            await self.write_str(reply)
        else:
            reply = "'''Error: (8) Timeout waiting for device answer"
            await self.write_str(reply)


class MockFanControlServer(tcpip.OneClientServer):
    def __init__(self):
        self.send_messages_task = utils.make_done_future()
        self._status = False
        self._did_change = False
        super().__init__(host=tcpip.LOCAL_HOST, port=0, log=logging.getLogger(__name__))

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, status):
        self._status = status
        self._did_change = True

    async def start(self, **kwargs):
        self.send_messages_task = asyncio.create_task(self.send_messages())
        return await super().start(**kwargs)

    async def close(self):
        self.send_messages_task.cancel()
        return await super().close()

    async def send_messages(self):
        self.status = False
        while True:
            if self.connected:
                msg = {"status": self.status}
                if self._did_change:
                    await self.write_json(msg)
                    self._did_change = False
            await asyncio.sleep(1)


class MockLaserAlignmentServer(tcpip.OneClientServer):
    def __init__(self):
        self.send_messages_task = utils.make_done_future()
        self._status = False
        self._did_change = False
        super().__init__(host=tcpip.LOCAL_HOST, port=0, log=logging.getLogger(__name__))

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, status):
        self._status = status
        self._did_change = True

    async def start(self, **kwargs):
        self.send_messages_task = asyncio.create_task(self.send_messages())
        return await super().start(**kwargs)

    async def close(self):
        self.send_messages_task.cancel()
        return await super().close()

    async def send_messages(self):
        self.status = False
        while True:
            if self.connected:
                msg = {"status": self.status}
                if self._did_change:
                    await self.write_json(msg)
                    self._did_change = False
            await asyncio.sleep(1)


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
            self.log.error(f"TempCtrlServer hostname was invalid, assuming temp ctrler unconnected: {host}")
            super().__init__(
                name="TempCtrl Mock Server",
                host=tcpip.LOCAL_HOST,
                port=50000,
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
            await self.write(reply.encode(self.encoding))
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

                bcc_frame = self.node + subadd + SID + self.MRC + self.SRC + self.cmd_txt + "\x03"

                bcc_maker = CompoWayFGeneralRegister()
                expected_bcc = bcc_maker.generate_bcc(frame=bcc_frame)

                self.bcc = f.read(1).decode()
                if expected_bcc is not self.bcc:
                    raise ValueError(f"Mismatch of BCC, got: {self.bcc}, expected: {expected_bcc}")

                # some type of read/write variable address cmd
                if self.MRC == "\x30\x31" and (self.SRC == "\x30\x31" or self.SRC == "\x30\x32"):
                    self.var_type = self.cmd_txt[:2]
                    self.address = self.cmd_txt[2:6]
                    bit_pos = self.cmd_txt[6:8]
                    if bit_pos != "\x30\x30":
                        self.log.error(f"got incorrect bitposition, expected 00, got: {bit_pos}")
                    self.num_of_elements = self.cmd_txt[8:12]

                    if self.SRC == "\x30\x32":
                        self.write_data = self.cmd_txt[12:]
                elif self.MRC == "\x33\x30" and self.SRC == "\x30\x35":  # 30 05 operation reg
                    self.command_code = self.cmd_txt[:2]
                    self.related_info = self.cmd_txt[2:4]
                else:
                    raise ValueError(f"Command not supported, got MRC {self.MRC} SRC {self.SRC}")
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
                    raise ValueError("More than 1 number of element read/write not supported")

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
            "\x30\x30": True,  # on
            "\x30\x31": False,  # off
        }
        if data in run_stop_related_info:
            self.run_stop = run_stop_related_info[data]
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


class BaseMockEksplaLaser:
    """Shared ASCII command handling for Ekspla laser mocks."""

    def __init__(self):
        self.log = logging.getLogger(__name__)
        self.wavelength = random.randrange(1, 1100)
        self.temperature = random.randrange(19, 21)
        self.cpu8000_current = "19A"
        self.m_cpu800_current = "19A"
        self.cpu8000_power = Power.ON
        self.m_cpu800_power = Power.ON
        self.propagating = Power.OFF
        self.output_energy_level = Output.OFF
        self.propagation_mode = Mode.CONTINUOUS
        self.burst_length = 1
        self.frequency_divider = 1
        self.qsw_adjustment_output_delay = 308
        self.repetition_rate = 1
        self.synchronization_mode = 0
        self.diode_current_on = "ON"
        self.external_interlock_state = "Defeated"
        self.ph532_power = "0.002"
        self.ldco48bp_48_temperature = "31.00"
        self.ldco48bp_50_temperature = "28.00"
        self.tk6_44_temperature = "50.00"
        self.tk6_45_temperature = "50.12"

    def _normalize_token(self, token):
        token = token.strip().lower()
        token = token.replace("%2f", "_").replace("/", "_").replace(" ", "_")
        token = re.sub(r"[^0-9a-z_]+", "_", token)
        token = re.sub(r"_+", "_", token).strip("_")
        return token

    def _make_command_name(self, register_name, register_id, register_field, has_parameter):
        prefix = "do_set_" if has_parameter else "do_"
        return (
            f"{prefix}{self._normalize_token(register_name)}_"
            f"{int(register_id)}_{self._normalize_token(register_field)}"
        )

    def parse_message(self, msg):
        """Parse a laser ASCII message and dispatch to a mock handler."""
        try:
            self.log.info(msg)
            parts = msg.strip().split("/")
            if parts and parts[0] == "":
                parts = parts[1:]
            if len(parts) < 3:
                raise ValueError("Message malformed")

            register_name = parts[0]
            register_id = parts[1]
            remaining = parts[2:]
            candidates = [("/".join(remaining), None)]
            if len(remaining) > 1:
                candidates.append(("/".join(remaining[:-1]), remaining[-1]))

            for register_field, parameter in candidates:
                command_name = self._make_command_name(
                    register_name=register_name,
                    register_id=register_id,
                    register_field=register_field,
                    has_parameter=parameter is not None,
                )
                self.log.debug(f"{command_name=}")
                handler = getattr(self, command_name, None)
                if handler is None:
                    continue
                reply = handler() if parameter is None else handler(parameter)
                self.log.debug(f"reply: {reply}")
                return reply

            self.log.error(f"command not implemented for message {msg}")
            return "NA"
        except Exception:
            self.log.exception("Unexpected exception occurred.")
            raise

    def check_limits(self, value, min, max):
        if int(float(value)) < min:
            return "'''Error: (12) Violating bottom value limit"
        if int(float(value)) > max:
            return "'''Error: (11) Violating top value limit"
        return ""

    def _wrong_value_error(self):
        return "'''Error: (13) Wrong value, not included in allowed values list"

    def _set_enum(self, attribute_name, enum_type, raw_value):
        try:
            if isinstance(raw_value, enum_type):
                value = raw_value
            elif isinstance(raw_value, str):
                try:
                    value = enum_type(raw_value)
                except ValueError:
                    try:
                        value = enum_type(int(raw_value))
                    except ValueError:
                        value = enum_type[raw_value.strip().upper()]
            else:
                value = enum_type(raw_value)
            setattr(self, attribute_name, value)
            return ""
        except (KeyError, TypeError, ValueError):
            self.log.error(f"{raw_value} not in {list(enum_type)}")
            return self._wrong_value_error()

    def _set_int_range(self, attribute_name, raw_value, min_value, max_value):
        reply = self.check_limits(raw_value, min_value, max_value)
        if not reply.startswith("'''"):
            setattr(self, attribute_name, int(float(raw_value)))
        return reply

    def do_cpu8000_16_power(self):
        return f"{self.cpu8000_power}"

    def do_set_cpu8000_16_power(self, state):
        return self._set_enum("cpu8000_power", Power, state)

    def do_m_cpu800_17_power(self):
        return f"{self.m_cpu800_power}"

    def do_set_m_cpu800_17_power(self, state):
        return self._set_enum("m_cpu800_power", Power, state)

    def do_m_cpu800_17_fault_code(self):
        return "0"

    def do_m_cpu800_17_display_current(self):
        return f"{self.m_cpu800_current}"

    def do_m_cpu800_18_power(self):
        return f"{self.propagating}"

    def do_set_m_cpu800_18_power(self, state):
        return self._set_enum("propagating", Power, state)

    def do_m_cpu800_18_fault_code(self):
        return "0"

    def do_m_cpu800_18_display_current(self):
        return f"{self.m_cpu800_current}"

    def do_cpu8000_16_display_current(self):
        return f"{self.cpu8000_current}"

    def do_cpu8000_16_fault_code(self):
        return "0"

    def do_m_cpu800_18_diode_current_on(self):
        return f"{self.diode_current_on}"

    def do_set_m_cpu800_18_diode_current_on(self, state):
        self.diode_current_on = state
        return ""

    def do_m_cpu800_18_continuous_burst_mode_trigger_burst(self):
        return f"{self.propagation_mode}"

    def do_set_m_cpu800_18_continuous_burst_mode_trigger_burst(self, mode):
        return self._set_enum("propagation_mode", Mode, mode)

    def do_m_cpu800_18_output_energy_level(self):
        return f"{self.output_energy_level}"

    def do_set_m_cpu800_18_output_energy_level(self, energy_level):
        return self._set_enum("output_energy_level", Output, energy_level)

    def do_m_cpu800_18_frequency_divider(self):
        return f"{self.frequency_divider}"

    def do_set_m_cpu800_18_frequency_divider(self, value):
        return self._set_int_range("frequency_divider", value, 1, 5000)

    def do_m_cpu800_18_burst_pulses_to_go(self):
        return "0"

    def do_m_cpu800_18_qsw_adjustment_output_delay(self):
        return f"{self.qsw_adjustment_output_delay}"

    def do_set_m_cpu800_18_qsw_adjustment_output_delay(self, value):
        return self._set_int_range("qsw_adjustment_output_delay", value, 50, 1000)

    def do_m_cpu800_18_repetition_rate(self):
        return f"{self.repetition_rate}"

    def do_set_m_cpu800_18_repetition_rate(self, value):
        return self._set_int_range("repetition_rate", value, 1, 11000)

    def do_m_cpu800_18_synchronization_mode(self):
        return f"{self.synchronization_mode}"

    def do_set_m_cpu800_18_synchronization_mode(self, value):
        return self._set_int_range("synchronization_mode", value, 0, 1)

    def do_m_cpu800_18_burst_length(self):
        return f"{self.burst_length}"

    def do_set_m_cpu800_18_burst_length(self, count):
        return self._set_int_range("burst_length", count, 1, 50000)

    def do_m_cpu800_18_external_interlock_state(self):
        return f"{self.external_interlock_state}"

    def do_tk6_44_display_temperature(self):
        return f"{self.tk6_44_temperature}"

    def do_tk6_44_set_temperature(self):
        return f"{self.tk6_44_temperature}"

    def do_set_tk6_44_set_temperature(self, value):
        reply = self.check_limits(value, -2300, 26600)
        if not reply.startswith("'''"):
            self.tk6_44_temperature = value
        return reply

    def do_tk6_45_display_temperature(self):
        return f"{self.tk6_45_temperature}"

    def do_tk6_45_set_temperature(self):
        return f"{self.tk6_45_temperature}"

    def do_set_tk6_45_set_temperature(self, value):
        reply = self.check_limits(value, -2300, 26600)
        if not reply.startswith("'''"):
            self.tk6_45_temperature = value
        return reply


class MockNT252(BaseMockEksplaLaser):
    """Implement the mock NT252 device."""

    def __init__(self) -> None:
        super().__init__()
        self.log.debug("MockNT252 initialized")

    def do_ph_532_55_power(self):
        return f"{self.ph532_power}"

    def do_midiopg_31_wavelength(self):
        return f"{self.wavelength}nm"

    def do_set_midiopg_31_wavelength(self, wavelength):
        return self._set_int_range("wavelength", wavelength, 1, 2600)

    def do_midiopg_31_status(self):
        return "Ok."

    def do_ldco48bp_48_set_temperature(self):
        return f"{self.ldco48bp_48_temperature}"

    def do_set_ldco48bp_48_set_temperature(self, value):
        reply = self.check_limits(value, -200, 4600)
        if not reply.startswith("'''"):
            self.ldco48bp_48_temperature = value
        return reply

    def do_ldco48bp_50_set_temperature(self):
        return f"{self.ldco48bp_50_temperature}"

    def do_set_ldco48bp_50_set_temperature(self, value):
        reply = self.check_limits(value, -200, 4600)
        if not reply.startswith("'''"):
            self.ldco48bp_50_temperature = value
        return reply

    def do_ldco48bp_48_display_temperature(self):
        return f"{self.ldco48bp_48_temperature}"

    def do_ldco48bp_50_display_temperature(self):
        return f"{self.ldco48bp_50_temperature}"

    def do_ldco48bp_28_error_code(self):
        return "0"

    def do_ldco48bp_29_error_code(self):
        return "0"

    def do_m_ldco48_33_error_code(self):
        return "0"

    def do_m_ldco48_34_error_code(self):
        return "0"

    def do_hv40w_40_error_code(self):
        return "0"

    def do_fopo_51_error_code(self):
        return "0"

    def do_sopo_52_error_code(self):
        return "0"

    def do_sh1_53_error_code(self):
        return "0"

    def do_c1_54_error_code(self):
        return "0"


class MockNT900(BaseMockEksplaLaser):
    """Implements a mock NT900 laser."""

    def __init__(self):
        super().__init__()
        self.scu = False
        if not self.scu:
            self.configuration = OpticalConfiguration.NO_SCU
        else:
            self.configuration = OpticalConfiguration.SCU
        self.log.debug("MockNT900 initialized")

    def do_maxiopg_31_wavelength(self):
        return f"{self.wavelength}nm"

    def do_set_maxiopg_31_wavelength(self, wavelength):
        return self._set_int_range("wavelength", wavelength, 300, 1100)

    def do_11pmku_54_power(self):
        return "19A"

    def do_maxiopg_31_configuration(self):
        return f"{self.configuration}"

    def do_set_maxiopg_31_configuration(self, configuration):
        try:
            self.configuration = OpticalConfiguration(configuration)
            return ""
        except ValueError:
            self.log.error(f"{configuration} not in {list(OpticalConfiguration)}")
            return self._wrong_value_error()

    def do_miniopg_56_error_code(self):
        return "0"

    def do_set_temperature(self):
        return f"{self.temperature}C"

    def do_hv40w_41_hv_voltage(self):
        return "10"

    def do_delaylin_40_error_code(self):
        return "0"

    def do_ldco48bp_30_display_temperature(self):
        return f"{self.temperature}"

    def do_ldco48bp_29_display_temperature(self):
        return f"{self.temperature}"

    def do_ldco48bp_24_display_temperature(self):
        return f"{self.temperature}"

    def do_m_ldco48_33_display_temperature(self):
        return f"{self.temperature}"

    def do_m_ldco48_34_display_temperature(self):
        return f"{self.temperature}"
