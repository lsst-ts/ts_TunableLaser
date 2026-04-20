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

__all__ = ["Laser", "CompoWayFModule", "CompoWayFRegisterModule"]

import asyncio
from abc import ABC, abstractmethod

from lsst.ts import tcpip
from lsst.ts.tunablelaser.wizardry import DEFAULT_SLEEP, NUMBER_OF_RETRIES

from .compoway_register import CompoWayFDataRegister, CompoWayFGeneralRegister, CompoWayFOperationRegister
from .register import AsciiRegister


class Laser(ABC):
    """Implement common Laser interface.

    Parameters
    ----------
    csc : `LaserCSC`
        The CSC object.
    terminator : `bytes`
        The characters that terminate sent/received messages.
    encoding : `str`
        The type of encoding to use.
    simulation_mode : `bool`, optional
        Is the laser being simulated?

    Attributes
    ----------
    csc : `LaserCSC`
        The CSC object.
    terminator : `bytes`
        The characters that terminate sent/received messages.
    encoding : `str`
        The type of encoding to use.
    log : `logging.Logger`
        The log of the component.
    simulation_mode : `bool`
        Is the laser being simulated?
    commander : `lsst.ts.tcpip.Client`
        A TCP/IP client.
    """

    def __init__(self, log, terminator, encoding, simulation_mode=False) -> None:
        self.terminator = terminator
        self.encoding = encoding
        self.log = log
        self.simulation_mode = simulation_mode
        self.commander = tcpip.Client(host="", port=0, log=self.log)
        self.lock = asyncio.Lock()

    @property
    @abstractmethod
    def is_propagating(self):
        """Is the laser propagating?"""
        raise NotImplementedError

    @property
    def connected(self):
        """Is the laser connected?"""
        return self.commander.connected

    @property
    def should_be_connected(self):
        return self.commander.should_be_connected

    @property
    @abstractmethod
    def wavelength(self):
        """The wavelength of the laser."""
        raise NotImplementedError

    @property
    @abstractmethod
    def temperature(self):
        """The temperature sensors."""
        raise NotImplementedError

    @property
    @abstractmethod
    def propagation_mode(self):
        raise NotImplementedError

    @property
    @abstractmethod
    def optical_configuration(self):
        raise NotImplementedError

    @abstractmethod
    def change_wavelength(self, wavelength):
        """Change the wavelength.

        Parameters
        ----------
        wavelength: `float`
            The value to change the wavelength.
        """
        raise NotImplementedError

    @abstractmethod
    def set_output_energy_level(self, output_energy_level):
        """Set the output energy level.

        Parameters
        ----------
        output_energy_level:
            The laser's energy level.
        """
        raise NotImplementedError

    @abstractmethod
    def trigger_burst(self):
        """Trigger burst."""
        raise NotImplementedError

    @abstractmethod
    def set_burst_mode(self, count):
        """Set the burst mode and count."""
        raise NotImplementedError

    @abstractmethod
    def start_propagating(self):
        """Start propagating the laser."""
        raise NotImplementedError

    @abstractmethod
    def stop_propagating(self):
        """Stop propagating the laser."""
        raise NotImplementedError

    @abstractmethod
    def clear_fault(self):
        """Clear the fault state of the laser."""
        raise NotImplementedError

    @abstractmethod
    def configure(self, config):
        """Configure the laser."""
        raise NotImplementedError

    async def disconnect(self):
        """Disconnect from the laser."""
        await self.commander.close()
        self.commander = tcpip.Client(host="", port=0, log=self.log)

    async def send_command(self, message):
        resp = None
        async with self.lock:
            await self.commander.write(message.encode(self.commander.encoding))
            for _ in range(NUMBER_OF_RETRIES):
                try:
                    resp = await self.commander.read_str()
                except TimeoutError:
                    self.log.warning("Response timed out... Waiting to try again.")
                    await asyncio.sleep(DEFAULT_SLEEP)
                if resp:
                    if resp.startswith("'''"):
                        self.log.exception("Command failed.")
                        raise RuntimeError("Command failed.")
                    else:
                        return resp.rstrip("nmC\r\n")
            if not resp:
                raise RuntimeError("Response not received.")

    def _iter_canbus_modules(self):
        for value in vars(self).values():
            if isinstance(value, CanbusModule):
                yield value

    async def read_register(self, register):
        register.register_value = await self.send_command(register.create_get_message())
        return register.register_value

    async def write_register(self, register, value):
        await self.send_command(register.create_set_message(value))
        return await self.read_register(register)

    async def refresh_all_ascii_registers(self):
        """Refresh all ascii registers attached to this laser."""
        for module in self._iter_canbus_modules():
            for register in module.iter_ascii_registers():
                await self.read_register(register)

    async def connect(self):
        """Connect to the laser."""
        for _ in range(NUMBER_OF_RETRIES):
            try:
                self.commander = tcpip.Client(
                    host=self.host,
                    port=self.port,
                    log=self.log,
                    terminator=bytes(self.terminator),
                    encoding=self.encoding,
                )
                await self.commander.start_task
            except Exception:
                self.log.exception("Connection failed.")
            if self.commander.connected:
                break
        if not self.commander.connected:
            raise RuntimeError("Connect call failed.")


class CanbusModule(ABC):
    """Implement a register container for the laser."""

    async def update_register(self, read_register):
        """Update the registers located in the canbus module."""
        for register in self.iter_ascii_registers():
            await read_register(register)

    def iter_ascii_registers(self):
        for value in vars(self).values():
            if isinstance(value, AsciiRegister):
                yield value


class CompoWayFModule(ABC):
    """Implement CompoWayF Module.

    Parameters
    ----------
    csc : `LaserCSC`
        The CSC object.
    terminator : `bytes`
        The characters that terminate sent/received messages.
    encoding : `str`
        The type of encoding to use.
    simulation_mode : `bool`, optional
        Is the laser being simulated?

    Attributes
    ----------
    csc : `LaserCSC`
        The CSC object.
    terminator : `bytes`
        The characters that terminate sent/received messages.
    encoding : `str`
        The type of encoding to use.
    log : `logging.Logger`
        The log of the component.
    simulation_mode : `bool`
        Is the module being simulated?
    commander : `lsst.ts.tcpip.Client`
        A TCP/IP client.
    """

    def __init__(self, log, terminator=b"\x03", encoding="utf-8", simulation_mode=False) -> None:
        self.encoding = encoding
        self.log = log
        self.simulation_mode = simulation_mode
        self.terminator = terminator
        self.commander = tcpip.Client(host="", port=0, log=self.log)
        self.lock = asyncio.Lock()

    @property
    def connected(self):
        """Is the module connected?"""
        return self.commander.connected

    @property
    @abstractmethod
    def temperature(self):
        """The temperature sensors."""
        raise NotImplementedError

    @abstractmethod
    def configure(self, config):
        """Configure the module."""
        raise NotImplementedError

    async def disconnect(self):
        """Disconnect from the module."""
        await self.commander.close()
        self.commander = tcpip.Client(host="", port=0, log=self.log)

    def _iter_compoway_modules(self):
        for value in vars(self).values():
            if isinstance(value, CompoWayFRegisterModule):
                yield value

    async def refresh_all_registers(self):
        """Refresh all CompoWay registers attached to the controller."""
        for module in self._iter_compoway_modules():
            for register in module.iter_compoway_registers():
                if isinstance(register, CompoWayFDataRegister):
                    await self.read_register(register)

    def _expected_node_subaddress(self, register):
        expected = "\x02"
        if int(register.node) < 10:
            expected += "\x30"
        expected += register.node + "\x30\x30"
        return expected

    async def _write_frame(self, frame, simulation_mode=False):
        if simulation_mode:
            frame += "\r"
        await self.commander.write(frame.encode(self.commander.encoding))

    async def _read_common_response_header(self, register, expected_mrc_src):
        stx_node_subadd = await self.commander.readexactly(5)
        stx_node_subadd = stx_node_subadd.decode()
        expected_stx_node_subadd = self._expected_node_subaddress(register)
        if stx_node_subadd != expected_stx_node_subadd:
            self.log.error(
                f"Received incorrect start of packet: {stx_node_subadd}, expected: {expected_stx_node_subadd}"
            )

        register.end_code = await self.commander.readexactly(2)
        register.end_code = register.end_code.decode()

        mrc_src = await self.commander.readexactly(4)
        mrc_src = mrc_src.decode()
        if mrc_src != expected_mrc_src:
            self.log.error(f"Received incorrect Request Codes: {mrc_src}, expected: {expected_mrc_src}")

        register.response_code = await self.commander.readexactly(4)
        register.response_code = register.response_code.decode()

        return stx_node_subadd, mrc_src

    async def _handle_data_read_response(self, register):
        stx_node_subadd, mrc_src = await self._read_common_response_header(register, "\x30\x31\x30\x31")

        register.cmd_txt = await self.commander.readuntil(b"\x03")
        register.cmd_txt = register.cmd_txt.decode()[:-1]
        try:
            register.register_value = int(register.cmd_txt, 16)
        except Exception as e:
            self.log.error(f"Received no valid register value! {register.cmd_txt} {str(e)}")
            register.register_value = -1

        register.bcc = await self.commander.readexactly(1)
        register.bcc = register.bcc.decode()

        bcc_frame = (
            stx_node_subadd.split("\x02")[1]
            + register.end_code
            + mrc_src
            + register.response_code
            + register.cmd_txt
            + "\x03"
        )
        expected_bcc = register.generate_bcc(bcc_frame)
        if expected_bcc != register.bcc:
            self.log.error(f"Incorrect BCC, got: {register.bcc}, expected: {expected_bcc}")
            register.register_value = -1

        return register.register_value

    async def _handle_write_response(self, register, expected_mrc_src):
        stx_node_subadd, mrc_src = await self._read_common_response_header(register, expected_mrc_src)

        if register.end_code != "\x30\x30":
            end_code_text = register.end_code_dict.get(register.end_code, "Unknown end code")
            self.log.error(f"Received bad end code: {register.end_code}: {end_code_text}")
        if register.response_code != "\x30\x30\x30\x30":
            response_text = register.response_dict.get(register.response_code, "Unknown response code")
            self.log.error(f"Received bad response code: {register.response_code}: {response_text}")

        etx = await self.commander.readuntil(b"\x03")
        etx = etx.decode()
        if etx != "\x03":
            self.log.error(f"Received bad ETX: {etx} expected: \x03")

        register.bcc = await self.commander.readexactly(1)
        register.bcc = register.bcc.decode()

        bcc_frame = (
            stx_node_subadd.split("\x02")[1] + register.end_code + mrc_src + register.response_code + "\x03"
        )
        expected_bcc = register.generate_bcc(bcc_frame)
        if expected_bcc != register.bcc:
            self.log.error(f"Incorrect BCC, got: {register.bcc}, expected: {expected_bcc}")

    async def read_register(self, register):
        async with self.lock:
            await self._write_frame(register.create_get_message(), simulation_mode=register.simulation_mode)
            try:
                return await self._handle_data_read_response(register)
            except Exception as e:
                self.log.error(f"Message format not as expected. Message: {e}")
                return register.register_value

    async def write_register(self, register, value):
        if isinstance(register, CompoWayFOperationRegister):
            async with self.lock:
                await self._write_frame(
                    register.create_set_message(value), simulation_mode=register.simulation_mode
                )
                await self._handle_write_response(register, "\x33\x30\x30\x35")
            register.register_value = value
            return register.register_value

        if isinstance(register, CompoWayFDataRegister):
            if register.simulation_mode:
                register.register_value = value
                return register.register_value

            async with self.lock:
                await self._write_frame(
                    register.create_set_message(value), simulation_mode=register.simulation_mode
                )
                await self._handle_write_response(register, "\x30\x31\x30\x32")
            return await self.read_register(register)

        raise TypeError(f"Unsupported CompoWay register type: {type(register)!r}")

    async def connect(self):
        """Connect to the module."""
        if self.host is not None:
            self.commander = tcpip.Client(
                host=self.host,
                port=self.port,
                log=self.log,
                terminator=bytes(self.terminator),
                encoding=self.encoding,
            )
            await self.commander.start_task


class CompoWayFRegisterModule(ABC):
    """Container for CompoWay registers attached to temperature controller."""

    def iter_compoway_registers(self):
        for value in vars(self).values():
            if isinstance(value, CompoWayFGeneralRegister):
                yield value

    async def update_register(self, read_register):
        for register in self.iter_compoway_registers():
            if isinstance(register, CompoWayFDataRegister):
                await read_register(register)
