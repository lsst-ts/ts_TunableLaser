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

from lsst.ts import tcpip, utils

from .compoway_register import CompoWayFGeneralRegister
from .enums import Mode, OpticalConfiguration, Output, Power
from .wizardry import (
    MOCK_COMPOWAY_READ_CAP,
    MOCK_SERVER_TERMINATOR,
    MOCK_STABLE_REPLY_WEIGHT,
    MOCK_STATUS_PUBLISH_INTERVAL,
    MOCK_UNSTABLE_REPLY_WEIGHT,
)


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
            terminator=MOCK_SERVER_TERMINATOR,
        )

    async def read_and_dispatch(self):
        """Read one ASCII command and write the mock Stubbs response.

        Raises
        ------
        asyncio.IncompleteReadError
            Raised by the underlying stream if the client disconnects before a
            complete command is read.
        """
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
            terminator=MOCK_SERVER_TERMINATOR,
            encoding="ascii",
        )

    async def read_and_dispatch(self):
        """Read one ASCII command and write the simulated laser response.

        Raises
        ------
        asyncio.IncompleteReadError
            Raised by the underlying stream if the client disconnects before a
            complete command is read.
        """
        if self.simulate_connection_unstability:
            unstable = random.choices(
                [True, False],
                [MOCK_UNSTABLE_REPLY_WEIGHT, MOCK_STABLE_REPLY_WEIGHT],
            )
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
    """Simulate the fan-control status side-channel server.

    Attributes
    ----------
    send_messages_task : `asyncio.Future` or `asyncio.Task`
        Background publisher task.
    status : `bool`
        Current simulated fan-control status.
    """

    def __init__(self):
        self.send_messages_task = utils.make_done_future()
        self._status = False
        self._did_change = False
        super().__init__(host=tcpip.LOCAL_HOST, port=0, log=logging.getLogger(__name__))

    @property
    def status(self):
        """Current fan-control status.

        Returns
        -------
        status : `bool`
            Current simulated fan-control status.
        """
        return self._status

    @status.setter
    def status(self, status):
        """Set fan-control status and mark it for publication.

        Parameters
        ----------
        status : `bool`
            New simulated status value.
        """
        self._status = status
        self._did_change = True

    async def start(self, **kwargs):
        """Start the server and its status publishing task.

        Parameters
        ----------
        **kwargs
            Keyword arguments forwarded to the superclass ``start`` method.

        Returns
        -------
        result : `object`
            Result returned by the superclass ``start`` method.
        """
        self.send_messages_task = asyncio.create_task(self.send_messages())
        return await super().start(**kwargs)

    async def close(self):
        """Close the server and cancel its status publishing task.

        Returns
        -------
        result : `object`
            Result returned by the superclass ``close`` method.
        """
        self.send_messages_task.cancel()
        return await super().close()

    async def send_messages(self):
        """Publish status messages when the simulated status changes.

        Raises
        ------
        asyncio.CancelledError
            Raised when the background task is cancelled during server close.
        """
        self.status = False
        while True:
            if self.connected:
                msg = {"status": self.status}
                if self._did_change:
                    await self.write_json(msg)
                    self._did_change = False
            await asyncio.sleep(MOCK_STATUS_PUBLISH_INTERVAL)


class MockLaserAlignmentServer(tcpip.OneClientServer):
    """Simulate the laser-alignment status side-channel server.

    Attributes
    ----------
    send_messages_task : `asyncio.Future` or `asyncio.Task`
        Background publisher task.
    status : `bool`
        Current simulated laser-alignment status.
    """

    def __init__(self):
        self.send_messages_task = utils.make_done_future()
        self._status = False
        self._did_change = False
        super().__init__(host=tcpip.LOCAL_HOST, port=0, log=logging.getLogger(__name__))

    @property
    def status(self):
        """Current laser-alignment status.

        Returns
        -------
        status : `bool`
            Current simulated laser-alignment status.
        """
        return self._status

    @status.setter
    def status(self, status):
        """Set laser-alignment status and mark it for publication.

        Parameters
        ----------
        status : `bool`
            New simulated status value.
        """
        self._status = status
        self._did_change = True

    async def start(self, **kwargs):
        """Start the server and its status publishing task.

        Parameters
        ----------
        **kwargs
            Keyword arguments forwarded to the superclass ``start`` method.

        Returns
        -------
        result : `object`
            Result returned by the superclass ``start`` method.
        """
        self.send_messages_task = asyncio.create_task(self.send_messages())
        return await super().start(**kwargs)

    async def close(self):
        """Close the server and cancel its status publishing task.

        Returns
        -------
        result : `object`
            Result returned by the superclass ``close`` method.
        """
        self.send_messages_task.cancel()
        return await super().close()

    async def send_messages(self):
        """Publish status messages when the simulated status changes.

        Raises
        ------
        asyncio.CancelledError
            Raised when the background task is cancelled during server close.
        """
        self.status = False
        while True:
            if self.connected:
                msg = {"status": self.status}
                if self._did_change:
                    await self.write_json(msg)
                    self._did_change = False
            await asyncio.sleep(MOCK_STATUS_PUBLISH_INTERVAL)


class TempCtrlServer(tcpip.OneClientReadLoopServer):
    """Simulates the tcpip server for the temp ctrl.

    Parameters
    ----------
    host : `str`, optional
        The host interface that the server will bind.
    port : `int`, optional
        The port that the server will start on.
    """

    def __init__(self, host=tcpip.LOCAL_HOST, port=0) -> None:
        self.device = MockNP5450()
        self.log = logging.getLogger(__name__)
        self.read_loop_task = asyncio.Future()
        super().__init__(
            name="TempCtrl Mock Server",
            host=host,
            port=port,
            log=self.log,
            terminator=b"\r",
            encoding="ascii",
        )

    async def read_and_dispatch(self):
        """Read one CompoWay-F command and write the temperature response.

        Raises
        ------
        asyncio.IncompleteReadError
            Raised by the underlying stream if the client disconnects before a
            complete command is read.
        """
        if self.device is not None:
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
        """Return a multiline representation of the parsed ASCII message.

        Returns
        -------
        representation : `str`
            Multiline summary of the parsed register name, ID, and field.
        """
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
                for _ in range(MOCK_COMPOWAY_READ_CAP):
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
        """Return a multiline representation of the parsed CompoWay-F message.

        Returns
        -------
        representation : `str`
            Multiline summary of parsed node, command, payload, and BCC.
        """
        return f"{self.node}\n{self.MRC}\n{self.SRC}\n{self.cmd_txt}\n{self.bcc}"


class MockNP5450:
    """Implements a mock NP5450 .

    Attributes
    ----------
    e5dcb_setpoint_temperature : `str` or `int`
        Simulated E5DCB setpoint payload.
    run_stop : `bool`
        Simulated run/stop state.
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
        value : `int` or `str`
            The value to check.
        min : `int`
            The minimum value.
        max : `int`
            The max value

        Returns
        -------
        reply : `str`
            Empty string for success, or a vendor-style range error.
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
        reply : `str`
            The reply of the command parsed.

        Raises
        ------
        Exception
            Raised if the command cannot be parsed or dispatched.
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
        """Set the simulated Omron setpoint.

        Parameters
        ----------
        data : `str`
            Encoded setpoint payload.

        Returns
        -------
        reply : `str`
            CompoWay-F write acknowledgement.
        """
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
        """Return the simulated Omron setpoint response.

        Returns
        -------
        reply : `str`
            CompoWay-F data-read response containing the setpoint payload.
        """
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
        """Set the simulated Omron run/stop state.

        Parameters
        ----------
        data : `str`
            Encoded operation-register related-info payload.

        Returns
        -------
        reply : `str`
            CompoWay-F operation acknowledgement.
        """
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
        temperature : `str`
            Temperature setpoint formatted with a ``C`` suffix.
        """
        return f"{self.e5dcb_setpoint_temperature}C"


class BaseMockEksplaLaser:
    """Shared ASCII command handling for Ekspla laser mocks.

    Attributes
    ----------
    wavelength : `int`
        Simulated wavelength in nanometers.
    propagation_mode : `Mode`
        Simulated propagation mode.
    output_energy_level : `Output`
        Simulated output energy setting.
    """

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
        self.synchronization_mode = "Internal"
        self.diode_current_on = "ON"
        self.external_interlock_state = "Defeated"
        self.ph532_power = "0.002"
        self.ldco48bp_48_temperature = "31.00"
        self.ldco48bp_50_temperature = "28.00"
        self.tk6_44_temperature = "50.00"
        self.tk6_45_temperature = "50.12"

    def _normalize_token(self, token):
        """Normalize an ASCII command path token into a Python identifier part.

        Parameters
        ----------
        token : `str`
            Raw module or register path token.

        Returns
        -------
        normalized : `str`
            Lowercase identifier-safe token.
        """
        token = token.strip().lower()
        token = token.replace("%2f", "_").replace("/", "_").replace(" ", "_")
        token = re.sub(r"[^0-9a-z_]+", "_", token)
        token = re.sub(r"_+", "_", token).strip("_")
        return token

    def _make_command_name(self, register_name, register_id, register_field, has_parameter):
        """Build the mock handler name for an ASCII command.

        Parameters
        ----------
        register_name : `str`
            Module name token from the command path.
        register_id : `str`
            Numeric module ID token from the command path.
        register_field : `str`
            Register name token from the command path.
        has_parameter : `bool`
            Whether the command includes a value to write.

        Returns
        -------
        command_name : `str`
            Handler method name to look up on the mock device.
        """
        prefix = "do_set_" if has_parameter else "do_"
        return (
            f"{prefix}{self._normalize_token(register_name)}_"
            f"{int(register_id)}_{self._normalize_token(register_field)}"
        )

    def parse_message(self, msg):
        """Parse a laser ASCII message and dispatch to a mock handler.

        Parameters
        ----------
        msg : `str`
            The raw message decoded.

        Returns
        -------
        reply : `str`
            The reply received from the mock device.

        Raises
        ------
        ValueError
            Raised if the message path is malformed.
        Exception
            Re-raised if a handler fails unexpectedly.
        """
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
        """Check whether a numeric value is inside inclusive limits.

        Parameters
        ----------
        value : `str` or `float`
            Value to validate.
        min : `int`
            Inclusive lower bound.
        max : `int`
            Inclusive upper bound.

        Returns
        -------
        reply : `str`
            Empty string for success, or a vendor-style error string.
        """
        if int(float(value)) < min:
            return "'''Error: (12) Violating bottom value limit"
        if int(float(value)) > max:
            return "'''Error: (11) Violating top value limit"
        return ""

    def _wrong_value_error(self):
        """Return the wrong value error message.

        Returns
        -------
        reply : `str`
            Vendor-style wrong-value error response.
        """
        return "'''Error: (13) Wrong value, not included in allowed values list"

    def _set_enum(self, attribute_name, enum_type, raw_value):
        """Set a mock enum-valued register.

        Parameters
        ----------
        attribute_name : `str`
            Mock device attribute to update.
        enum_type : `type`
            Enum class that defines accepted values.
        raw_value : `object`
            Value received from the ASCII command.

        Returns
        -------
        reply : `str`
            Empty string for success, or a vendor-style wrong-value error.
        """
        try:
            if isinstance(raw_value, enum_type):
                value = raw_value
            elif isinstance(raw_value, str):
                try:
                    value = enum_type(raw_value)
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
        """Set a mock integer register after range validation.

        Parameters
        ----------
        attribute_name : `str`
            Mock device attribute to update.
        raw_value : `str`
            Value received from the ASCII command.
        min_value : `int`
            Inclusive lower bound.
        max_value : `int`
            Inclusive upper bound.

        Returns
        -------
        reply : `str`
            Empty string for success, or a vendor-style range error.
        """
        reply = self.check_limits(raw_value, min_value, max_value)
        if not reply.startswith("'''"):
            setattr(self, attribute_name, int(float(raw_value)))
        return reply

    def do_cpu8000_16_power(self):
        """Return the simulated CPU8000 power state.

        Returns
        -------
        reply : `str`
            Current CPU8000 power state.
        """
        return f"{self.cpu8000_power}"

    def do_set_cpu8000_16_power(self, state):
        """Set the simulated CPU8000 power state.

        Parameters
        ----------
        state : `str`
            Requested power state.

        Returns
        -------
        reply : `str`
            Empty string for success, or a vendor-style wrong-value error.
        """
        return self._set_enum("cpu8000_power", Power, state)

    def do_m_cpu800_17_power(self):
        """Return the simulated M_CPU800 controller power state.

        Returns
        -------
        reply : `str`
            Current M_CPU800 controller power state.
        """
        return f"{self.m_cpu800_power}"

    def do_set_m_cpu800_17_power(self, state):
        """Set the simulated M_CPU800 controller power state.

        Parameters
        ----------
        state : `str`
            Requested power state.

        Returns
        -------
        reply : `str`
            Empty string for success, or a vendor-style wrong-value error.
        """
        return self._set_enum("m_cpu800_power", Power, state)

    def do_m_cpu800_17_fault_code(self):
        """Return the simulated M_CPU800 controller fault code.

        Returns
        -------
        reply : `str`
            Simulated fault code.
        """
        return "0"

    def do_m_cpu800_17_display_current(self):
        """Return the simulated M_CPU800 controller current.

        Returns
        -------
        reply : `str`
            Simulated controller current.
        """
        return f"{self.m_cpu800_current}"

    def do_m_cpu800_18_power(self):
        """Return the simulated propagation power state.

        Returns
        -------
        reply : `str`
            Current propagation power state.
        """
        return f"{self.propagating}"

    def do_set_m_cpu800_18_power(self, state):
        """Set the simulated propagation power state.

        Parameters
        ----------
        state : `str`
            Requested power state.

        Returns
        -------
        reply : `str`
            Empty string for success, or a vendor-style wrong-value error.
        """
        return self._set_enum("propagating", Power, state)

    def do_m_cpu800_18_fault_code(self):
        """Return the simulated propagation fault code.

        Returns
        -------
        reply : `str`
            Simulated fault code.
        """
        return "0"

    def do_m_cpu800_18_display_current(self):
        """Return the simulated propagation current.

        Returns
        -------
        reply : `str`
            Simulated propagation current.
        """
        return f"{self.m_cpu800_current}"

    def do_cpu8000_16_display_current(self):
        """Return the simulated CPU8000 current.

        Returns
        -------
        reply : `str`
            Simulated CPU8000 current.
        """
        return f"{self.cpu8000_current}"

    def do_cpu8000_16_fault_code(self):
        """Return the simulated CPU8000 fault code.

        Returns
        -------
        reply : `str`
            Simulated fault code.
        """
        return "0"

    def do_m_cpu800_18_diode_current_on(self):
        """Return the simulated diode-current state.

        Returns
        -------
        reply : `str`
            Simulated diode-current state.
        """
        return f"{self.diode_current_on}"

    def do_set_m_cpu800_18_diode_current_on(self, state):
        """Set the simulated diode-current state.

        Parameters
        ----------
        state : `str`
            Requested diode-current state.

        Returns
        -------
        reply : `str`
            Empty string for success.
        """
        self.diode_current_on = state
        return ""

    def do_m_cpu800_18_continuous_burst_mode_trigger_burst(self):
        """Return the simulated propagation mode.

        Returns
        -------
        reply : `str`
            Current propagation mode.
        """
        return f"{self.propagation_mode}"

    def do_set_m_cpu800_18_continuous_burst_mode_trigger_burst(self, mode):
        """Set the simulated propagation mode.

        Parameters
        ----------
        mode : `str`
            Requested propagation mode.

        Returns
        -------
        reply : `str`
            Empty string for success, or a vendor-style wrong-value error.
        """
        return self._set_enum("propagation_mode", Mode, mode)

    def do_m_cpu800_18_output_energy_level(self):
        """Return the simulated output energy level.

        Returns
        -------
        reply : `str`
            Current output energy level.
        """
        return f"{self.output_energy_level}"

    def do_set_m_cpu800_18_output_energy_level(self, energy_level):
        """Set the simulated output energy level.

        Parameters
        ----------
        energy_level : `str`
            Requested output energy level.

        Returns
        -------
        reply : `str`
            Empty string for success, or a vendor-style wrong-value error.
        """
        return self._set_enum("output_energy_level", Output, energy_level)

    def do_m_cpu800_18_frequency_divider(self):
        """Return the simulated frequency divider.

        Returns
        -------
        reply : `str`
            Current frequency divider.
        """
        return f"{self.frequency_divider}"

    def do_set_m_cpu800_18_frequency_divider(self, value):
        """Set the simulated frequency divider.

        Parameters
        ----------
        value : `str`
            Requested frequency divider.

        Returns
        -------
        reply : `str`
            Empty string for success, or a vendor-style range error.
        """
        return self._set_int_range("frequency_divider", value, 1, 5000)

    def do_m_cpu800_18_burst_pulses_to_go(self):
        """Return the simulated remaining burst-pulse count.

        Returns
        -------
        reply : `str`
            Simulated remaining burst-pulse count.
        """
        return "0"

    def do_m_cpu800_18_qsw_adjustment_output_delay(self):
        """Return the simulated QSW adjustment output delay.

        Returns
        -------
        reply : `str`
            Current QSW adjustment output delay.
        """
        return f"{self.qsw_adjustment_output_delay}"

    def do_set_m_cpu800_18_qsw_adjustment_output_delay(self, value):
        """Set the simulated QSW adjustment output delay.

        Parameters
        ----------
        value : `str`
            Requested output delay.

        Returns
        -------
        reply : `str`
            Empty string for success, or a vendor-style range error.
        """
        return self._set_int_range("qsw_adjustment_output_delay", value, 50, 1000)

    def do_m_cpu800_18_repetition_rate(self):
        """Return the simulated repetition rate.

        Returns
        -------
        reply : `str`
            Current repetition rate.
        """
        return f"{self.repetition_rate}"

    def do_set_m_cpu800_18_repetition_rate(self, value):
        """Set the simulated repetition rate.

        Parameters
        ----------
        value : `str`
            Requested repetition rate.

        Returns
        -------
        reply : `str`
            Empty string for success, or a vendor-style range error.
        """
        return self._set_int_range("repetition_rate", value, 1, 11000)

    def do_m_cpu800_18_synchronization_mode(self):
        """Return the simulated synchronization mode.

        Returns
        -------
        reply : `str`
            Current synchronization mode.
        """
        return f"{self.synchronization_mode}"

    def do_set_m_cpu800_18_synchronization_mode(self, value):
        """Set the simulated synchronization mode.

        Parameters
        ----------
        value : `str`
            Requested synchronization mode.

        Returns
        -------
        reply : `str`
            Empty string for success, or a vendor-style wrong-value error.
        """
        accepted_values = ["Internal", "External"]
        if value not in accepted_values:
            self.log.error(f"{value} not in {accepted_values}")
            return self._wrong_value_error()
        self.synchronization_mode = value
        return ""

    def do_m_cpu800_18_burst_length(self):
        """Return the simulated burst length.

        Returns
        -------
        reply : `str`
            Current burst length.
        """
        return f"{self.burst_length}"

    def do_set_m_cpu800_18_burst_length(self, count):
        """Set the simulated burst length.

        Parameters
        ----------
        count : `str`
            Requested burst length.

        Returns
        -------
        reply : `str`
            Empty string for success, or a vendor-style range error.
        """
        return self._set_int_range("burst_length", count, 1, 50000)

    def do_m_cpu800_18_external_interlock_state(self):
        """Return the simulated external interlock state.

        Returns
        -------
        reply : `str`
            Current external interlock state.
        """
        return f"{self.external_interlock_state}"

    def do_tk6_44_display_temperature(self):
        """Return the simulated TK6 module 44 display temperature.

        Returns
        -------
        reply : `str`
            Current TK6 module 44 display temperature.
        """
        return f"{self.tk6_44_temperature}"

    def do_tk6_44_set_temperature(self):
        """Return the simulated TK6 module 44 set temperature.

        Returns
        -------
        reply : `str`
            Current TK6 module 44 set temperature.
        """
        return f"{self.tk6_44_temperature}"

    def do_set_tk6_44_set_temperature(self, value):
        """Set the simulated TK6 module 44 temperature setpoint.

        Parameters
        ----------
        value : `str`
            Requested setpoint.

        Returns
        -------
        reply : `str`
            Empty string for success, or a vendor-style range error.
        """
        reply = self.check_limits(value, -2300, 26600)
        if not reply.startswith("'''"):
            self.tk6_44_temperature = value
        return reply

    def do_tk6_45_display_temperature(self):
        """Return the simulated TK6 module 45 display temperature.

        Returns
        -------
        reply : `str`
            Current TK6 module 45 display temperature.
        """
        return f"{self.tk6_45_temperature}"

    def do_tk6_45_set_temperature(self):
        """Return the simulated TK6 module 45 set temperature.

        Returns
        -------
        reply : `str`
            Current TK6 module 45 set temperature.
        """
        return f"{self.tk6_45_temperature}"

    def do_set_tk6_45_set_temperature(self, value):
        """Set the simulated TK6 module 45 temperature setpoint.

        Parameters
        ----------
        value : `str`
            Requested setpoint.

        Returns
        -------
        reply : `str`
            Empty string for success, or a vendor-style range error.
        """
        reply = self.check_limits(value, -2300, 26600)
        if not reply.startswith("'''"):
            self.tk6_45_temperature = value
        return reply


class MockNT252(BaseMockEksplaLaser):
    """Implement the mock NT252 device.

    Notes
    -----
    Handler methods return string payloads that emulate the laser ASCII API.
    Writable handlers return an empty string on success or a vendor-style
    error string on failure.
    """

    def __init__(self) -> None:
        super().__init__()
        self.log.debug("MockNT252 initialized")

    def do_ph_532_55_power(self):
        """Return the simulated PH_532 power.

        Returns
        -------
        reply : `str`
            Current PH_532 power value.
        """
        return f"{self.ph532_power}"

    def do_midiopg_31_wavelength(self):
        """Return the simulated MidiOPG wavelength.

        Returns
        -------
        reply : `str`
            Current wavelength with ``nm`` suffix.
        """
        return f"{self.wavelength}nm"

    def do_set_midiopg_31_wavelength(self, wavelength):
        """Set the simulated MidiOPG wavelength.

        Parameters
        ----------
        wavelength : `str`
            Requested wavelength in nanometers.

        Returns
        -------
        reply : `str`
            Empty string for success, or a vendor-style range error.
        """
        return self._set_int_range("wavelength", wavelength, 1, 2600)

    def do_midiopg_31_status(self):
        """Return the simulated MidiOPG status.

        Returns
        -------
        reply : `str`
            Simulated status string.
        """
        return "Ok."

    def do_ldco48bp_48_set_temperature(self):
        """Return the simulated LDCO48BP module 48 set temperature.

        Returns
        -------
        reply : `str`
            Current module 48 temperature setpoint.
        """
        return f"{self.ldco48bp_48_temperature}"

    def do_set_ldco48bp_48_set_temperature(self, value):
        """Set the simulated LDCO48BP module 48 temperature setpoint.

        Parameters
        ----------
        value : `str`
            Requested setpoint.

        Returns
        -------
        reply : `str`
            Empty string for success, or a vendor-style range error.
        """
        reply = self.check_limits(value, -200, 4600)
        if not reply.startswith("'''"):
            self.ldco48bp_48_temperature = value
        return reply

    def do_ldco48bp_50_set_temperature(self):
        """Return the simulated LDCO48BP module 50 set temperature.

        Returns
        -------
        reply : `str`
            Current module 50 temperature setpoint.
        """
        return f"{self.ldco48bp_50_temperature}"

    def do_set_ldco48bp_50_set_temperature(self, value):
        """Set the simulated LDCO48BP module 50 temperature setpoint.

        Parameters
        ----------
        value : `str`
            Requested setpoint.

        Returns
        -------
        reply : `str`
            Empty string for success, or a vendor-style range error.
        """
        reply = self.check_limits(value, -200, 4600)
        if not reply.startswith("'''"):
            self.ldco48bp_50_temperature = value
        return reply

    def do_ldco48bp_48_display_temperature(self):
        """Return the simulated LDCO48BP module 48 display temperature.

        Returns
        -------
        reply : `str`
            Current module 48 display temperature.
        """
        return f"{self.ldco48bp_48_temperature}"

    def do_ldco48bp_50_display_temperature(self):
        """Return the simulated LDCO48BP module 50 display temperature.

        Returns
        -------
        reply : `str`
            Current module 50 display temperature.
        """
        return f"{self.ldco48bp_50_temperature}"

    def do_ldco48bp_28_error_code(self):
        """Return the simulated LDCO48BP module 28 error code.

        Returns
        -------
        reply : `str`
            Simulated error code.
        """
        return "0"

    def do_ldco48bp_29_error_code(self):
        """Return the simulated LDCO48BP module 29 error code.

        Returns
        -------
        reply : `str`
            Simulated error code.
        """
        return "0"

    def do_m_ldco48_33_error_code(self):
        """Return the simulated M_LDCO48 module 33 error code.

        Returns
        -------
        reply : `str`
            Simulated error code.
        """
        return "0"

    def do_m_ldco48_34_error_code(self):
        """Return the simulated M_LDCO48 module 34 error code.

        Returns
        -------
        reply : `str`
            Simulated error code.
        """
        return "0"

    def do_hv40w_40_error_code(self):
        """Return the simulated HV40W error code.

        Returns
        -------
        reply : `str`
            Simulated error code.
        """
        return "0"

    def do_fopo_51_error_code(self):
        """Return the simulated FOPO error code.

        Returns
        -------
        reply : `str`
            Simulated error code.
        """
        return "0"

    def do_sopo_52_error_code(self):
        """Return the simulated SOPO error code.

        Returns
        -------
        reply : `str`
            Simulated error code.
        """
        return "0"

    def do_sh1_53_error_code(self):
        """Return the simulated SH1 error code.

        Returns
        -------
        reply : `str`
            Simulated error code.
        """
        return "0"

    def do_c1_54_error_code(self):
        """Return the simulated C1 error code.

        Returns
        -------
        reply : `str`
            Simulated error code.
        """
        return "0"


class MockNT900(BaseMockEksplaLaser):
    """Implements a mock NT900 laser.

    Attributes
    ----------
    scu : `bool`
        Whether the simulated spectral cleaning unit path is active.
    configuration : `OpticalConfiguration`
        Simulated optical configuration.
    """

    def __init__(self):
        super().__init__()
        self.scu = False
        if not self.scu:
            self.configuration = OpticalConfiguration.NO_SCU
        else:
            self.configuration = OpticalConfiguration.SCU
        self.log.debug("MockNT900 initialized")

    def do_maxiopg_31_wavelength(self):
        """Return the simulated MaxiOPG wavelength.

        Returns
        -------
        reply : `str`
            Current wavelength with ``nm`` suffix.
        """
        return f"{self.wavelength}nm"

    def do_set_maxiopg_31_wavelength(self, wavelength):
        """Set the simulated MaxiOPG wavelength.

        Parameters
        ----------
        wavelength : `str`
            Requested wavelength in nanometers.

        Returns
        -------
        reply : `str`
            Empty string for success, or a vendor-style range error.
        """
        return self._set_int_range("wavelength", wavelength, 300, 1100)

    def do_11pmku_54_power(self):
        """Return the simulated 11PMKU power.

        Returns
        -------
        reply : `str`
            Simulated 11PMKU power value.
        """
        return "19A"

    def do_maxiopg_31_configuration(self):
        """Return the simulated MaxiOPG optical configuration.

        Returns
        -------
        reply : `str`
            Current optical configuration.
        """
        return f"{self.configuration}"

    def do_set_maxiopg_31_configuration(self, configuration):
        """Set the simulated MaxiOPG optical configuration.

        Parameters
        ----------
        configuration : `str`
            Requested optical configuration.

        Returns
        -------
        reply : `str`
            Empty string for success, or a vendor-style wrong-value error.
        """
        try:
            self.configuration = OpticalConfiguration(configuration)
            return ""
        except ValueError:
            self.log.error(f"{configuration} not in {list(OpticalConfiguration)}")
            return self._wrong_value_error()

    def do_miniopg_56_error_code(self):
        """Return the simulated MiniOPG error code.

        Returns
        -------
        reply : `str`
            Simulated error code.
        """
        return "0"

    def do_set_temperature(self):
        """Return the simulated NT900 temperature.

        Returns
        -------
        reply : `str`
            Simulated temperature with ``C`` suffix.
        """
        return f"{self.temperature}C"

    def do_hv40w_41_hv_voltage(self):
        """Return the simulated HV40W voltage.

        Returns
        -------
        reply : `str`
            Simulated HV40W voltage.
        """
        return "10"

    def do_delaylin_40_error_code(self):
        """Return the simulated DelayLin error code.

        Returns
        -------
        reply : `str`
            Simulated error code.
        """
        return "0"

    def do_ldco48bp_30_display_temperature(self):
        """Return the simulated LDCO48BP module 30 display temperature.

        Returns
        -------
        reply : `str`
            Current module 30 display temperature.
        """
        return f"{self.temperature}"

    def do_ldco48bp_29_display_temperature(self):
        """Return the simulated LDCO48BP module 29 display temperature.

        Returns
        -------
        reply : `str`
            Current module 29 display temperature.
        """
        return f"{self.temperature}"

    def do_ldco48bp_24_display_temperature(self):
        """Return the simulated LDCO48BP module 24 display temperature.

        Returns
        -------
        reply : `str`
            Current module 24 display temperature.
        """
        return f"{self.temperature}"

    def do_m_ldco48_33_display_temperature(self):
        """Return the simulated M_LDCO48 module 33 display temperature.

        Returns
        -------
        reply : `str`
            Current module 33 display temperature.
        """
        return f"{self.temperature}"

    def do_m_ldco48_34_display_temperature(self):
        """Return the simulated M_LDCO48 module 34 display temperature.

        Returns
        -------
        reply : `str`
            Current module 34 display temperature.
        """
        return f"{self.temperature}"
