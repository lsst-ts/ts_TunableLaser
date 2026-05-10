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

from typing import Iterator

__all__ = ["Laser", "CompoWayFModule", "CompoWayFRegisterModule"]

import asyncio
import logging
from abc import ABC, abstractmethod

from lsst.ts import tcpip
from lsst.ts.tunablelaser.wizardry import (
    BCC_LEN,
    COMMAND_TIMEOUT,
    DEFAULT_CONNECT_TIMEOUT,
    DEFAULT_SLEEP,
    DEVICE_TIMEOUT_READ_DELAY,
    DEVICE_TIMEOUT_READ_RETRIES,
    END_CODE_LEN,
    MRC_SRC_LEN,
    NUMBER_OF_CONNECTION_RETRIES,
    NUMBER_OF_RETRIES,
    RESPONSE_CODE_LENGTH,
    SLEEP_BETWEEN_REGISTERS,
    STX_NODE_SUBADDRESS_LEN,
)

from .compoway_register import CompoWayFDataRegister, CompoWayFGeneralRegister, CompoWayFOperationRegister
from .register import AsciiRegister

ERRORS = [
    "(8) Timeout waiting for device answer",
    "(6) No such register name",
]


class DeviceTimeoutError(Exception):
    """The controller replied that a downstream device timed out."""


class Laser(ABC):
    """Implement common Laser interface.

    Parameters
    ----------
    log : `logging.Logger`
        Logger for this component.
    terminator : `bytes`
        The characters that terminate sent/received messages.
    encoding : `str`
        The type of encoding to use.
    simulation_mode : `bool`, optional
        Is the laser being simulated?

    Attributes
    ----------
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

    def __init__(
        self, log: logging.Logger, terminator: bytes, encoding: str, simulation_mode: bool = False
    ) -> None:
        self.terminator = terminator
        self.encoding = encoding
        self.log = log
        self.simulation_mode = simulation_mode
        self.commander = tcpip.Client(host="", port=0, log=self.log)
        self.lock = asyncio.Lock()
        self.connect_lock = asyncio.Lock()
        self.connect_timeout = DEFAULT_CONNECT_TIMEOUT
        self.skipped_modules = set()
        self.skipped_registers = set()

    @property
    @abstractmethod
    def is_faulting(self) -> bool:
        """Return whether the laser reports a fault condition.

        Raises
        ------
        NotImplementedError
            Raised by the abstract base implementation.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def is_propagating(self) -> None:
        """Return whether the laser is propagating.

        Raises
        ------
        NotImplementedError
            Raised by the abstract base implementation.
        """
        raise NotImplementedError

    @property
    def connected(self) -> bool:
        """Return whether the laser is connected.

        Returns
        -------
        connected : `bool`
            `True` if the TCP/IP client is connected, else `False`.
        """
        return self.commander.connected

    @property
    def should_be_connected(self) -> bool:
        """Return whether the TCP/IP client expects to remain connected.

        Returns
        -------
        should_be_connected : `bool`
            `True` if the TCP/IP client expects to remain connected, else
            `False`.
        """
        return self.commander.should_be_connected

    @property
    @abstractmethod
    def wavelength(self) -> float:
        """The wavelength of the laser.

        Raises
        ------
        NotImplementedError
            Raised by the abstract base implementation.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def temperature(self) -> float:
        """The temperature sensors.

        Raises
        ------
        NotImplementedError
            Raised by the abstract base implementation.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def propagation_mode(self) -> str:
        """The laser propagation mode.

        Raises
        ------
        NotImplementedError
            Raised by the abstract base implementation.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def optical_configuration(self) -> str:
        """The selected optical output configuration.

        Raises
        ------
        NotImplementedError
            Raised by the abstract base implementation.
        """
        raise NotImplementedError

    @abstractmethod
    def change_wavelength(self, wavelength: float) -> str:
        """Change the wavelength.

        Parameters
        ----------
        wavelength: `float`
            The value to change the wavelength.

        Raises
        ------
        NotImplementedError
            Raised by the abstract base implementation.
        """
        raise NotImplementedError

    @abstractmethod
    def set_output_energy_level(self, output_energy_level) -> str:
        """Set the output energy level.

        Parameters
        ----------
        output_energy_level : `str`
            The laser's energy level.

        Raises
        ------
        NotImplementedError
            Raised by the abstract base implementation.
        """
        raise NotImplementedError

    @abstractmethod
    def trigger_burst(self) -> str:
        """Trigger burst.

        Raises
        ------
        NotImplementedError
            Raised by the abstract base implementation.
        """
        raise NotImplementedError

    @abstractmethod
    def set_burst_mode(self, count: int) -> str:
        """Set the burst mode and count.

        Parameters
        ----------
        count : `int`
            Number of pulses to emit in burst mode.

        Raises
        ------
        NotImplementedError
            Raised by the abstract base implementation.
        """
        raise NotImplementedError

    @abstractmethod
    def start_propagating(self) -> str:
        """Start propagating the laser.

        Raises
        ------
        NotImplementedError
            Raised by the abstract base implementation.
        """
        raise NotImplementedError

    @abstractmethod
    def stop_propagating(self) -> str:
        """Stop propagating the laser.

        Raises
        ------
        NotImplementedError
            Raised by the abstract base implementation.
        """
        raise NotImplementedError

    @abstractmethod
    def clear_fault(self) -> str:
        """Clear the fault state of the laser.

        Raises
        ------
        NotImplementedError
            Raised by the abstract base implementation.
        """
        raise NotImplementedError

    @abstractmethod
    def configure(self, config) -> None:
        """Configure the laser.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Runtime configuration for this laser.

        Raises
        ------
        NotImplementedError
            Raised by the abstract base implementation.
        """
        raise NotImplementedError

    async def _disconnect(self) -> None:
        # Public disconnect acquires connect_lock before calling this.
        # connect calls this directly because it already holds connect_lock,
        # avoiding re-entry into the non-reentrant asyncio.Lock.
        await self.commander.close()
        self.commander = self.create_empty_client()

    async def disconnect(self) -> None:
        """Disconnect from the laser."""
        async with self.connect_lock:
            await self._disconnect()

    async def _reconnect_after_timeout(self) -> bool:
        """Reconnect after a command timeout.

        A command timeout can leave a late response in the TCP stream. Reusing
        the same client for a retry can then pair the retry with stale bytes
        from the previous command.
        """
        try:
            await self.disconnect()
        except Exception:
            self.log.exception("Failed to close commander after command timeout.")
            return False

        if not hasattr(self, "host") or not hasattr(self, "port"):
            self.log.error("Cannot reconnect after timeout because host/port are not configured.")
            return False

        try:
            await self.connect()
        except Exception:
            self.log.exception("Failed to reconnect after command timeout.")
            return False

        return self.commander.connected

    async def send_command(self, message) -> str:
        """Send one ASCII command and return the decoded response.

        Parameters
        ----------
        message : `str`
            ASCII command frame, including its terminator.

        Returns
        -------
        response : `str`
            Response with common unit suffixes and line terminators stripped.

        Raises
        ------
        DeviceTimeoutError
            Raised when the laser reports a transient downstream device error.
        RuntimeError
            Raised when the laser reports a non-retryable ASCII error.
        ConnectionError
            Raised when retries are exhausted without a usable response.
        """
        last_error = None
        for attempt in range(NUMBER_OF_RETRIES):
            try:
                async with self.lock:
                    async with asyncio.timeout(COMMAND_TIMEOUT):
                        await self.commander.write(message.encode(self.commander.encoding))
                        resp = await self.commander.read_str()
                    if resp:
                        if resp.startswith("'''"):
                            self.log.error(f"{message} failed. Received {resp}.")
                            if any(error in resp for error in ERRORS):
                                raise DeviceTimeoutError(resp)
                            raise RuntimeError(f"{message} failed.")
                        return resp.rstrip("nmC\r\n")
            except asyncio.TimeoutError as err:
                last_error = err
                self.log.warning(
                    f"Command failed on attempt {attempt + 1}/{NUMBER_OF_RETRIES} for {message!r}: {err!r}"
                )
                if attempt == NUMBER_OF_RETRIES - 1:
                    break
                if not await self._reconnect_after_timeout():
                    break
                await asyncio.sleep(DEFAULT_SLEEP)
        raise ConnectionError("Response not received after retry exhaustion.") from last_error

    def _iter_canbus_modules(self) -> Iterator["CanbusModule"]:
        """Iterate over CAN bus module attributes attached to this laser.

        Yields
        ------
        module : `CanbusModule`
            A CAN bus module stored on this instance.
        """
        for value in vars(self).values():
            if isinstance(value, CanbusModule):
                yield value

    def should_poll_module(self, module) -> bool:
        """Return whether a CAN bus module should be polled.

        Parameters
        ----------
        module : `CanbusModule`
            Module being considered for telemetry polling.

        Returns
        -------
        should_poll : `bool`
            `True` if the module is not in ``skipped_modules``.
        """
        return module.name not in self.skipped_modules

    def register_poll_key(self, module, register) -> str:
        """Build the skip-list key for a register.

        Parameters
        ----------
        module : `CanbusModule`
            Module containing the register.
        register : `AsciiRegister`
            Register to identify.

        Returns
        -------
        key : `str`
            Key in ``"<module name>.<register name>"`` form.
        """
        return f"{module.name}.{register.register_name}"

    def should_poll_register(self, module, register) -> bool:
        """Return whether a register should be polled for telemetry.

        Parameters
        ----------
        module : `CanbusModule`
            Module containing the register.
        register : `AsciiRegister`
            Register being considered for telemetry polling.

        Returns
        -------
        should_poll : `bool`
            `True` if neither the module nor register is skipped.
        """
        return (
            self.should_poll_module(module)
            and self.register_poll_key(module, register) not in self.skipped_registers
        )

    async def read_register(self, register) -> str:
        """Read an ASCII register with device-timeout retries.

        Parameters
        ----------
        register : `AsciiRegister`
            Register to read.

        Returns
        -------
        value : `str`
            Decoded register value.

        Raises
        ------
        DeviceTimeoutError
            Raised when retry attempts are exhausted.
        """
        last_error = None
        for attempt in range(DEVICE_TIMEOUT_READ_RETRIES + 1):
            try:
                register.register_value = await self.send_command(register.create_get_message())
                return register.register_value
            except DeviceTimeoutError as err:
                last_error = err
                self.log.warning(
                    f"Device timeout reading {register.module_name}.{register.register_name} "
                    f"attempt {attempt + 1}/{DEVICE_TIMEOUT_READ_RETRIES + 1}: {err}"
                )
                if attempt == DEVICE_TIMEOUT_READ_RETRIES:
                    break
                await asyncio.sleep(DEVICE_TIMEOUT_READ_DELAY)
        raise last_error

    async def write_register(self, register, value) -> str:
        """Write an ASCII register and read it back.

        Parameters
        ----------
        register : `AsciiRegister`
            Register to write.
        value : `object`
            Value accepted by the register.

        Returns
        -------
        value : `str`
            Register value read after the write completes.
        """
        await self.send_command(register.create_set_message(value))
        return await self.read_register(register)

    async def refresh_all_ascii_registers(self) -> None:
        """Refresh all ascii registers attached to this laser."""
        loop = asyncio.get_running_loop()
        refresh_time_start = loop.time()
        for module in self._iter_canbus_modules():
            if not self.should_poll_module(module):
                continue
            for register in module.iter_ascii_registers():
                if not self.should_poll_register(module, register):
                    continue
                await self.read_register(register)
                await asyncio.sleep(SLEEP_BETWEEN_REGISTERS)
        refresh_time_dt = loop.time() - refresh_time_start
        self.log.debug(f"Refresh all registers took {refresh_time_dt:.3f}s")

    def create_empty_client(self) -> tcpip.Client:
        return tcpip.Client(host="", port=0, log=self.log)

    async def connect(self) -> None:
        """Connect to the laser.

        Raises
        ------
        RuntimeError
            Raised if all connection attempts fail.
        """
        async with self.connect_lock:
            last_error = None
            if self.commander.connected:
                await self._disconnect()
            for _ in range(NUMBER_OF_CONNECTION_RETRIES):
                commander = self.create_empty_client()
                try:
                    commander = tcpip.Client(
                        host=self.host,
                        port=self.port,
                        log=self.log,
                        terminator=bytes(self.terminator),
                        encoding=self.encoding,
                    )
                    async with asyncio.timeout(self.connect_timeout):
                        await commander.start_task
                    if commander.connected:
                        self.commander = commander
                        return
                except Exception as e:
                    last_error = e
                    self.log.exception("Connection failed.")
                finally:
                    if not commander.connected:
                        await commander.close()
                await asyncio.sleep(DEFAULT_SLEEP)
        raise RuntimeError("Connect call failed.") from last_error


class CanbusModule(ABC):
    """Implement a register container for the laser."""

    async def update_register(self, read_register) -> None:
        """Update the registers located in the canbus module.

        Parameters
        ----------
        read_register : callable
            Coroutine function used to read each register.
        """
        for register in self.iter_ascii_registers():
            await read_register(register)

    def iter_ascii_registers(self) -> Iterator[AsciiRegister]:
        """Iterate over ASCII registers attached to this module.

        Yields
        ------
        register : `AsciiRegister`
            An ASCII register stored on this module.
        """
        for value in vars(self).values():
            if isinstance(value, AsciiRegister):
                yield value


class CompoWayFModule(ABC):
    """Implement CompoWayF Module.

    Parameters
    ----------
    log : `logging.Logger`
        Logger for this component.
    terminator : `bytes`
        The characters that terminate sent/received messages.
    encoding : `str`
        The type of encoding to use.
    simulation_mode : `bool`, optional
        Is the laser being simulated?

    Attributes
    ----------
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
        """Return whether the module is connected.

        Returns
        -------
        connected : `bool`
            `True` if the TCP/IP client is connected, else `False`.
        """
        return self.commander.connected

    @property
    @abstractmethod
    def temperature(self):
        """The temperature sensors.

        Raises
        ------
        NotImplementedError
            Raised by the abstract base implementation.
        """
        raise NotImplementedError

    @abstractmethod
    def configure(self, config):
        """Configure the module.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Runtime configuration for this module.

        Raises
        ------
        NotImplementedError
            Raised by the abstract base implementation.
        """
        raise NotImplementedError

    async def disconnect(self):
        """Disconnect from the module."""
        await self.commander.close()
        self.commander = tcpip.Client(host="", port=0, log=self.log)

    def _iter_compoway_modules(self):
        """Iterate over CompoWay-F register modules attached to this
        controller.
        """
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
        """Build the expected CompoWay-F STX/node/subaddress prefix.

        Parameters
        ----------
        register : `CompoWayFGeneralRegister`
            Register whose node address is expected in the response.

        Returns
        -------
        prefix : `str`
            Expected start-of-frame, node, and subaddress text.
        """
        expected = "\x02"
        if int(register.node) < 10:
            expected += "\x30"
        expected += register.node + "\x30\x30"
        return expected

    async def _write_frame(self, frame, simulation_mode=False):
        """Write one CompoWay-F frame.

        Parameters
        ----------
        frame : `str`
            Encoded CompoWay-F frame text.
        simulation_mode : `bool`, optional
            If `True`, append a carriage return for the simulator transport.
        """
        if simulation_mode:
            frame += "\r"
        await self.commander.write(frame.encode(self.commander.encoding))

    async def _read_common_response_header(self, register, expected_mrc_src):
        """Read and validate the common CompoWay-F response header.

        Parameters
        ----------
        register : `CompoWayFGeneralRegister`
            Register receiving parsed response fields.
        expected_mrc_src : `str`
            Expected MRC/SRC response code text.

        Returns
        -------
        stx_node_subadd : `str`
            Start-of-frame, node, and subaddress text read from the response.
        mrc_src : `str`
            MRC/SRC response code text read from the response.
        """
        stx_node_subadd = await self.commander.readexactly(STX_NODE_SUBADDRESS_LEN)
        stx_node_subadd = stx_node_subadd.decode()
        expected_stx_node_subadd = self._expected_node_subaddress(register)
        if stx_node_subadd != expected_stx_node_subadd:
            self.log.error(
                f"Received incorrect start of packet: {stx_node_subadd}, expected: {expected_stx_node_subadd}"
            )

        register.end_code = await self.commander.readexactly(END_CODE_LEN)
        register.end_code = register.end_code.decode()

        mrc_src = await self.commander.readexactly(MRC_SRC_LEN)
        mrc_src = mrc_src.decode()
        if mrc_src != expected_mrc_src:
            self.log.error(f"Received incorrect Request Codes: {mrc_src}, expected: {expected_mrc_src}")

        register.response_code = await self.commander.readexactly(RESPONSE_CODE_LENGTH)
        register.response_code = register.response_code.decode()

        return stx_node_subadd, mrc_src

    async def _handle_data_read_response(self, register):
        """Read, decode, and validate a CompoWay-F data-read response.

        Parameters
        ----------
        register : `CompoWayFDataRegister`
            Register to update from the response.

        Returns
        -------
        value : `object`
            Decoded register value, or ``-1`` if payload or BCC validation
            fails.
        """
        stx_node_subadd, mrc_src = await self._read_common_response_header(register, "\x30\x31\x30\x31")

        register.cmd_txt = await self.commander.readuntil(b"\x03")
        register.cmd_txt = register.cmd_txt.decode()[:-1]
        try:
            raw_value = int(register.cmd_txt, 16)
            register.register_value = register.decode_register_value(raw_value)
        except Exception as e:
            self.log.error(f"Received no valid register value! {register.cmd_txt} {str(e)}")
            register.register_value = -1

        register.bcc = await self.commander.readexactly(BCC_LEN)
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
        """Read and validate a CompoWay-F write response.

        Parameters
        ----------
        register : `CompoWayFGeneralRegister`
            Register receiving parsed response fields.
        expected_mrc_src : `str`
            Expected MRC/SRC response code text for the write operation.
        """
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

        register.bcc = await self.commander.readexactly(BCC_LEN)
        register.bcc = register.bcc.decode()

        bcc_frame = (
            stx_node_subadd.split("\x02")[1] + register.end_code + mrc_src + register.response_code + "\x03"
        )
        expected_bcc = register.generate_bcc(bcc_frame)
        if expected_bcc != register.bcc:
            self.log.error(f"Incorrect BCC, got: {register.bcc}, expected: {expected_bcc}")

    async def read_register(self, register):
        """Read a CompoWay-F register.

        Parameters
        ----------
        register : `CompoWayFDataRegister`
            Register to read.

        Returns
        -------
        value : `object`
            Decoded register value, or the cached value if the response cannot
            be parsed.
        """
        async with self.lock:
            await self._write_frame(register.create_get_message(), simulation_mode=register.simulation_mode)
            try:
                return await self._handle_data_read_response(register)
            except Exception as e:
                self.log.error(f"Message format not as expected. Message: {e}")
                return register.register_value

    async def write_register(self, register, value):
        """Write a CompoWay-F register.

        Parameters
        ----------
        register : `CompoWayFDataRegister` or `CompoWayFOperationRegister`
            Register to write.
        value : `object`
            Value to write.

        Returns
        -------
        value : `object`
            Cached or read-back register value.

        Raises
        ------
        TypeError
            Raised if ``register`` is not a supported CompoWay-F register
            type.
        """
        if isinstance(register, CompoWayFOperationRegister):
            async with self.lock:
                await self._write_frame(
                    register.create_set_message(value), simulation_mode=register.simulation_mode
                )
                await self._handle_write_response(register, "\x33\x30\x30\x35")
            register.register_value = value
            return register.register_value

        if isinstance(register, CompoWayFDataRegister):
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
        """Iterate over CompoWay-F registers attached to this module.

        Yields
        ------
        register : `CompoWayFGeneralRegister`
            A CompoWay-F register stored on this module.
        """
        for value in vars(self).values():
            if isinstance(value, CompoWayFGeneralRegister):
                yield value

    async def update_register(self, read_register):
        """Refresh data registers attached to this module.

        Parameters
        ----------
        read_register : callable
            Coroutine function used to read each data register.
        """
        for register in self.iter_compoway_registers():
            if isinstance(register, CompoWayFDataRegister):
                await read_register(register)
