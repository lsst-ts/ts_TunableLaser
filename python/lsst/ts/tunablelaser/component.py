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
import logging

from lsst.ts import tcpip

from . import canbus_modules, interfaces
from .canbus import pgd217_nt252
from .enums import Mode, OpticalConfiguration, Power
from .fcu_client import FCUClient, Output
from .wizardry import (
    DEFAULT_LASER_WARMUP_DELAY,
    DEFAULT_TEMPERATURE_CTRL_PORT,
    MISSING_TEMPERATURE_VALUE,
    SIDE_CHANNEL_CLIENT_SLEEP,
    SIDE_CHANNEL_CLIENT_TIMEOUT,
)


def _coerce_enum(value, enum_type):
    """Best-effort conversion of cached ASCII values to an enum.

    Parameters
    ----------
    value : `object`
        Cached register value to convert.
    enum_type : `type`
        Enum class to convert ``value`` into.

    Returns
    -------
    `enum.Enum` or `object`
        The converted enum member, ``None`` if ``value`` is ``None``, or the
        original value if no conversion is possible.
    """
    if isinstance(value, enum_type):
        return value
    if value is None:
        return None
    try:
        return enum_type(value)
    except Exception:
        if isinstance(value, str):
            try:
                return enum_type[value.strip().upper()]
            except Exception:
                return value
        return value


def _matches_enum(value, enum_value):
    """Return whether a cached register value matches an enum member.

    Parameters
    ----------
    value : `object`
        Cached register value to compare.
    enum_value : `enum.Enum`
        Enum member expected by the caller.

    Returns
    -------
    `bool`
        `True` if ``value`` can be coerced to ``enum_value``.
    """
    return _coerce_enum(value, type(enum_value)) == enum_value


class MainLaser(interfaces.Laser):
    """The class that implements the TunableLaser component.

    Parameters
    ----------
    log : `logging.Logger`
        Logger for this component.
    simulation_mode : `bool`
        A flag which tells the component to initialize into simulation mode or
        not.
    encoding : `str`
        The type of encoding to use.
    terminator : `bytes`
        The terminating characters for messages sent/received.

    Attributes
    ----------
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
    m_ldcO48 : `MLDCO48`
        Controls the LDCO48 laser module.
    laser_warmup_delay : `float`
        The warmup delay before stating that the laser is propagating.
    lock : `asyncio.Lock`
        Lock the read/write operation.


    """

    def __init__(self, log, simulation_mode=False, encoding="ascii", terminator=b"\x03"):
        super().__init__(
            log=log,
            terminator=terminator,
            encoding=encoding,
            simulation_mode=simulation_mode,
        )
        self.cpu8000 = canbus_modules.CPU8000()
        self.m_cpu800 = canbus_modules.MCPU800()
        self.llpmku = canbus_modules.LLPMKU()
        self.maxi_opg = canbus_modules.MaxiOPG()
        self.tk6 = canbus_modules.TK6()
        self.hv40w = canbus_modules.HV40W()
        self.delay_lin = canbus_modules.DelayLin()
        self.mini_opg = canbus_modules.MiniOPG()
        self.ldco48bp = canbus_modules.LDCO48BP()
        self.m_ldcO48 = canbus_modules.MLDCO48()
        self.laser_warmup_delay = DEFAULT_LASER_WARMUP_DELAY
        self.lock = asyncio.Lock()

    @property
    def is_faulting(self):
        """Return whether any main-laser power register reports a fault.

        Returns
        -------
        is_faulting : `bool`
            `True` if any main-laser power register is in fault.
        """
        return (
            _matches_enum(self.cpu8000.power_register.register_value, Power.FAULT)
            or _matches_enum(self.m_cpu800.power_register.register_value, Power.FAULT)
            or _matches_enum(self.m_cpu800.power_register_2.register_value, Power.FAULT)
        )

    @property
    def optical_configuration(self):
        """Return the cached optical configuration.

        Returns
        -------
        optical_configuration : `object`
            Cached optical configuration register value.
        """
        return self.maxi_opg.configuration_register.register_value

    @property
    def propagation_mode(self):
        """Return the cached laser propagation mode.

        Returns
        -------
        propagation_mode : `Mode` or `object`
            Cached propagation mode, coerced to `Mode` when possible.
        """
        return _coerce_enum(self.m_cpu800.continous_burst_mode_trigger_burst_register.register_value, Mode)

    @property
    def is_propagating(self):
        """Return whether the propagation power register is on.

        Returns
        -------
        is_propagating : `bool`
            `True` if the propagation power register is on.
        """
        return _matches_enum(self.m_cpu800.power_register_2.register_value, Power.ON)

    @property
    def wavelength(self):
        """Return the cached wavelength.

        Returns
        -------
        wavelength : `object`
            Cached wavelength register value.
        """
        return self.maxi_opg.wavelength_register.register_value

    @property
    def temperature(self):
        """Return the cached laser temperature telemetry values.

        Returns
        -------
        temperatures : `tuple`
            Cached temperature register values.
        """
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
            This remains as float because it was used in other places.
            However, it should have been a long int.

            :Units: nanometers
        """
        self.log.debug("Changing wavelength")
        wave = int(wavelength)
        await self.write_register(*self.maxi_opg.change_wavelength(wave))

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
        await self.write_register(*self.maxi_opg.set_configuration())

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
        await self.write_register(*self.m_cpu800.set_output_energy_level(output_energy_level))

    async def trigger_burst(self):
        """Trigger a burst.

        Raises
        ------
        ValueError
            Raised when mode parameter is not in list of accepted values.
        """
        await self.write_register(*self.m_cpu800.set_propagation_mode(Mode.TRIGGER))

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
        await self.write_register(*self.m_cpu800.set_propagation_mode(Mode.BURST))
        await self.write_register(*self.m_cpu800.set_burst_count(count))

    async def set_continuous_mode(self):
        """Set the propagation mode to continuously pulse the laser."""
        await self.write_register(*self.m_cpu800.set_propagation_mode(Mode.CONTINUOUS))

    async def set_burst_count(self, count):
        """Set the burst count of the laser.

        Parameters
        ----------
        count : `int`
            The amount to pulse the laser.
        """
        await self.write_register(*self.m_cpu800.set_burst_count(count))

    async def start_propagating(self):
        """Start propagating the beam of the laser."""
        await self.write_register(*self.m_cpu800.start_propagating())
        await asyncio.sleep(self.laser_warmup_delay)  # laser warmup delay

    async def stop_propagating(self):
        """Stop propagating the beam of the laser"""
        await self.write_register(*self.m_cpu800.stop_propagating())

    async def clear_fault(self):
        """Clear the fault state of the laser."""
        if _matches_enum(self.m_cpu800.power_register_2.register_value, Power.FAULT):
            await self.read_register(self.m_cpu800.power_register_2)

    async def read_all_registers(self):
        """Publish the module's registers' values."""
        await self.refresh_all_ascii_registers()

    async def configure(self, config):
        """Set the configuration for the TunableLaser.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Configuration namespace supplied by the CSC.
        """
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
        """Return a compact string representation of the main laser modules."""
        return (
            f"{self.cpu8000} {self.m_cpu800} {self.llpmku} {self.maxi_opg} {self.mini_opg} {self.tk6}"
            f"{self.hv40w} {self.delay_lin} {self.ldco48bp} {self.m_ldcO48}"
        )


class StubbsLaser(interfaces.Laser):
    """Implement the Stubbs NT-252 laser.

    Parameters
    ----------
    log : `logging.Logger`
        Logger for this component.
    terminator : `bytes`
        The terminating characters for sent/received messages.
    encoding : `str`
        The type of encoding to use.
    simulation_mode : `bool`
        Is the laser in simulation mode?
    """

    def __init__(
        self,
        log: logging.Logger,
        terminator: bytes = b"\x03",
        encoding: str = "ascii",
        simulation_mode: bool = False,
    ) -> None:
        super().__init__(
            log=log,
            terminator=terminator,
            encoding=encoding,
            simulation_mode=simulation_mode,
        )
        self.midiopg = pgd217_nt252.MidiOPG()
        self.ph532 = pgd217_nt252.PH532()
        self.fopo = pgd217_nt252.FOPO()
        self.sopo = pgd217_nt252.SOPO()
        self.sh1 = pgd217_nt252.SH1()
        self.c1 = pgd217_nt252.C1()
        self.m_cpu800 = pgd217_nt252.MCPU800()
        self.cpu8000 = pgd217_nt252.CPU8000()
        self.tk6 = pgd217_nt252.TK6()
        self.hv40w = pgd217_nt252.HV40W()
        self.ldco48bp = pgd217_nt252.LDCO48BP()
        self.m_ldcO48 = pgd217_nt252.MLDCO48()
        self.fcu_client = FCUClient(simulation_mode=simulation_mode)
        self.laser_warmup_delay = DEFAULT_LASER_WARMUP_DELAY
        self.lock = asyncio.Lock()
        self.output_lut = {
            Output.out1: OpticalConfiguration.NO_SCU,
            Output.out2: OpticalConfiguration.F1_NO_SCU,
            Output.out3: OpticalConfiguration.F2_NO_SCU,
            None: None,
        }
        self.skipped_modules = {"PH_532", "FOPO", "SOPO", "SH1", "C1", "M_LDCO48", "HV40W"}
        self.skipped_registers = {
            "M_CPU800.Diode current ON",
            "M_CPU800.QSW Adjustment output delay",
            "M_CPU800.Frequency divider",
            "M_CPU800.Synchronization mode",
            "M_CPU800.Repetition rate",
            "M_CPU800.External interlock state",
            "M_CPU800.Display Current",
            "MidiOPG.Status",
            "LDCO48BP.Set temperature",
            "LDCO48BP.Error Code",
            "TK6.Set temperature",
            "CPU8000.Display Current",
        }

    @property
    def is_faulting(self) -> bool:
        """Return whether any Stubbs power register reports a fault.

        Returns
        -------
        is_faulting : `bool`
            `True` if any Stubbs power register is in fault.
        """
        return (
            _matches_enum(self.m_cpu800.power_id_0x11_register.register_value, Power.FAULT)
            or _matches_enum(self.m_cpu800.power_id_0x12_register.register_value, Power.FAULT)
            or _matches_enum(self.cpu8000.power_id_0x10_register.register_value, Power.FAULT)
        )

    @property
    def optical_configuration(self) -> None | OpticalConfiguration:
        """Return the optical configuration implied by the FCU output.

        Returns
        -------
        optical_configuration : `OpticalConfiguration` or `None`
            Optical configuration selected by the FCU output.
        """
        return self.output_lut[self.fcu_client.output]

    @property
    def propagation_mode(self) -> Mode:
        """Return the cached Stubbs propagation mode.

        Returns
        -------
        propagation_mode : `Mode`
            Cached propagation mode.
        """
        return _coerce_enum(
            self.m_cpu800.continuous_burst_mode_trigger_burst_id_0x12_register.register_value,
            Mode,
        )

    @property
    def is_propagating(self) -> Power:
        """Return whether the Stubbs propagation power register is on.

        Returns
        -------
        is_propagating : `bool`
            `True` if the Stubbs propagation power register is on.
        """
        return _matches_enum(self.m_cpu800.power_id_0x12_register.register_value, Power.ON)

    @property
    def wavelength(self) -> float:
        """Return the cached Stubbs wavelength.

        Returns
        -------
        wavelength : `float`
            Cached wavelength register value.
        """
        return self.midiopg.wavelength_id_0x1f_register.register_value

    @property
    def temperature(self) -> tuple[float, ...]:
        """Return cached Stubbs temperature telemetry values.

        Returns
        -------
        temperatures : `tuple` [`float`, ...]
            Cached Stubbs temperature telemetry values.
        """
        return (
            self.tk6.display_temperature_id_0x2c_register.register_value,
            MISSING_TEMPERATURE_VALUE,
            self.ldco48bp.display_temperature_id_0x30_register.register_value,
            self.ldco48bp.display_temperature_id_0x32_register.register_value,
            MISSING_TEMPERATURE_VALUE,
            MISSING_TEMPERATURE_VALUE,
            MISSING_TEMPERATURE_VALUE,
            MISSING_TEMPERATURE_VALUE,
        )

    async def set_optical_configuration(self, optical_configuration: OpticalConfiguration):
        """Set optical configuration.

        Parameters
        ----------
        optical_configuration : str
            The value to be set.

        Raises
        ------
        RuntimeError
            Raised if ``optical_configuration`` is not accepted.
        """
        match optical_configuration:
            case OpticalConfiguration.NO_SCU:
                await self.fcu_client.set_output(Output.out1)
            case OpticalConfiguration.F1_NO_SCU:
                await self.fcu_client.set_output(Output.out2)
            case OpticalConfiguration.F2_NO_SCU:
                await self.fcu_client.set_output(Output.out3)
            case OpticalConfiguration.SCU:
                await self.fcu_client.set_output(Output.out1)
            case OpticalConfiguration.F1_SCU:
                await self.fcu_client.set_output(Output.out2)
            case OpticalConfiguration.F2_SCU:
                await self.fcu_client.set_output(Output.out3)
            case _:
                raise RuntimeError("Not one of the acceptable configurations.")

    async def change_wavelength(self, wavelength: float):
        """Change the wavelength.

        Parameters
        ----------
        wavelength : float
            The wavelength to be set.
        """
        await self.write_register(self.midiopg.wavelength_id_0x1f_register, wavelength)

    async def set_output_energy_level(self, output_energy_level):
        """Set output energy level.

        Parameters
        ----------
        output_energy_level : `str`
            The output to be set.
        """
        await self.write_register(
            self.m_cpu800.output_energy_level_id_0x12_register,
            output_energy_level,
        )

    async def trigger_burst(self):
        """Trigger a burst.

        Raises
        ------
        ValueError
            Raised when mode parameter is not in list of accepted values.
        """
        await self.write_register(
            self.m_cpu800.continuous_burst_mode_trigger_burst_id_0x12_register, Mode.TRIGGER
        )
        await self.set_burst_mode(count=self.m_cpu800.burst_length_id_0x12_register.register_value)

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
        await self.write_register(
            self.m_cpu800.continuous_burst_mode_trigger_burst_id_0x12_register, Mode.BURST
        )
        await self.write_register(self.m_cpu800.burst_length_id_0x12_register, int(count))

    async def set_continuous_mode(self):
        """Set the propagation mode to continuously pulse the laser."""
        await self.write_register(
            self.m_cpu800.continuous_burst_mode_trigger_burst_id_0x12_register, Mode.CONTINUOUS
        )

    async def set_burst_count(self, count):
        """Set the burst count of the laser.

        Parameters
        ----------
        count : `int`
            The amount to pulse the laser.
        """
        await self.write_register(self.m_cpu800.burst_length_id_0x12_register, count)

    async def start_propagating(self):
        """Start propagating the beam of the laser."""
        await self.write_register(self.m_cpu800.power_id_0x12_register, Power.ON)
        await asyncio.sleep(self.laser_warmup_delay)  # laser warmup delay

    async def stop_propagating(self):
        """Stop propagating the beam of the laser"""
        await self.write_register(self.m_cpu800.power_id_0x12_register, Power.OFF)

    async def clear_fault(self):
        """Clear the fault state of the laser."""
        if _matches_enum(self.m_cpu800.power_id_0x12_register.register_value, Power.FAULT):
            await self.write_register(self.m_cpu800.power_id_0x12_register, Power.OFF)

    async def configure(self, config):
        """Configure host, port, and writable wavelength range.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Configuration namespace supplied by the CSC.
        """
        self.log.debug("Setting config.")
        self.host = config.host
        self.port = config.port

        self.midiopg.wavelength_id_0x1f_register.accepted_values = range(
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
        """Refresh Stubbs laser registers and FCU output state."""
        await self.refresh_all_ascii_registers()
        await self.fcu_client.get_output()


class TemperatureCtrl(interfaces.CompoWayFModule):
    """Implement the Omron Temperature Controller.

    Parameters
    ----------
    log : `logging.Logger`
        Logger for this component.
    host : `string`
        The IP address of the temp controller.
    port : `int`
        The port of the temp controller.
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
        The host for the temp controller.
    """

    def __init__(
        self,
        log,
        host="127.0.0.1",
        port=DEFAULT_TEMPERATURE_CTRL_PORT,
        terminator=b"\x03",
        encoding="ascii",
        simulation_mode=False,
    ) -> None:
        super().__init__(
            log=log,
            terminator=terminator,
            encoding=encoding,
            simulation_mode=simulation_mode,
        )

        # if host is not valid IP address assume its unconnected
        if str(host).lower() != "none":
            self.host = host
            self.e5dc_b = canbus_modules.E5DCB(simulation_mode=simulation_mode)
        else:
            self.log.error(f"Host address given to Temp Ctrl not valid, assuming unconnected: {host}")
            self.host = None
            self.e5dc_b = None
        self.port = port

    @property
    def temperature(self):
        """Return the cached temperature-controller setpoint.

        Returns
        -------
        temperature : `tuple` [`float`]
            One-item tuple containing the setpoint register value, or ``-1``
            if the temperature controller is disconnected.
        """
        if self.e5dc_b is not None:
            return (self.e5dc_b.set_point_register.register_value,)
        else:
            return (-1,)

    async def laser_thermal_turn_on(self):
        """Turn the heater and fans on."""
        if self.e5dc_b is not None:
            await self.write_register(self.e5dc_b.run_stop_register, True)
        else:
            self.log.error("Tried to laser_thermal_turn_on but thermal ctrler is unconnected.")

    async def laser_thermal_turn_off(self):
        """Turn the heater and fans off."""
        if self.e5dc_b is not None:
            await self.write_register(self.e5dc_b.run_stop_register, False)
        else:
            self.log.error("Tried to laser_thermal_turn_off but thermal ctrler is unconnected.")

    async def laser_thermal_change_set_point(self, value):
        """Change the temperature set point value.

        Parameters
        ----------
        value : `float`
            New temperature setpoint.
        """
        if self.e5dc_b is not None:
            await self.write_register(self.e5dc_b.set_point_register, value)
        else:
            self.log.error("Tried to laser_thermal_change_set_point but thermal ctrler is unconnected.")

    async def configure(self, config):
        """Configure the thermal controller.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Configuration namespace with ``host`` and ``port`` attributes.
        """
        self.log.debug("Setting config.")
        self.host = config.host
        self.port = config.port

    async def read_all_registers(self):
        """Read all of the registers."""
        if self.e5dc_b is not None:
            await self.refresh_all_registers()
        else:
            self.log.warning("Tried to update_register but thermal ctrler is unconnected.")


class FanControlClient:
    """Implement fan control client.

    Parameters
    ----------
    simulation_mode : `bool`, optional
        Is the client in simulation mode.

    Attributes
    ----------
    host : `str`
        The hostname.
    port : `int`
        The port.
    log : `logging.Logger`
        The log object.
    client : `tcpip.Client`
        The client.
    response : `None`
        The latest response.
    response_queue : `asyncio.Queue`
        Pending responses waiting to be consumed.
    """

    def __init__(self, simulation_mode: bool = False) -> None:
        self.host = ""
        self.port = None
        self.log = logging.getLogger(__name__)
        self.client = tcpip.Client(host=self.host, port=self.port, log=self.log)
        self.response = None
        self.response_queue = asyncio.Queue()

    @property
    def connected(self) -> bool:
        """Return whether the client is connected.

        Returns
        -------
        connected : `bool`
            `True` if the TCP/IP client is connected.
        """
        return self.client.connected

    async def connect(self) -> None:
        """Connect to the service."""
        self.client = tcpip.Client(host=self.host, port=self.port, log=self.log)
        await self.client.start_task

    async def disconnect(self) -> None:
        """Disconnect from the service."""
        await self.client.close()
        self.host = ""
        self.port = None
        self.client = tcpip.Client(host=self.host, port=self.port, log=self.log)

    async def get_messages(self) -> None:
        """Get messages received from the service."""
        while self.connected:
            try:
                async with asyncio.timeout(SIDE_CHANNEL_CLIENT_TIMEOUT):
                    response = await self.client.read_json()
                self.response = response
                self.response_queue.put_nowait(response)
            except asyncio.TimeoutError:
                self.log.exception("Response timed out")
            except (asyncio.IncompleteReadError, ConnectionError):
                break
            finally:
                await asyncio.sleep(SIDE_CHANNEL_CLIENT_SLEEP)


class LaserAlignmentClient:
    """Implement the laser alignment client.

    Attributes
    ----------
    host : `str`
        The hostname.
    port : `int`
        The port.
    log : `logging.Logger`
        The log object.
    client : `tcpip.Client`
        The client.
    response : `None`
        The latest response.
    response_queue : `asyncio.Queue`
        Pending responses waiting to be consumed.
    """

    def __init__(self):
        self.host = ""
        self.port = None
        self.log = logging.getLogger(__name__)
        self.response = None
        self.response_queue = asyncio.Queue()
        self.client = tcpip.Client(host=self.host, port=self.port, log=self.log)

    @property
    def connected(self):
        """Return whether the client is connected.

        Returns
        -------
        connected : `bool`
            `True` if the TCP/IP client is connected.
        """
        return self.client.connected

    async def connect(self):
        """Connect to the service."""
        self.client = tcpip.Client(host=self.host, port=self.port, log=self.log)
        await self.client.start_task

    async def disconnect(self):
        """Disconnect from the service."""
        await self.client.close()
        self.host = ""
        self.port = None
        self.client = tcpip.Client(host=self.host, port=self.port, log=self.log)

    async def get_messages(self):
        """Get messages received from the service."""
        while self.connected:
            try:
                async with asyncio.timeout(SIDE_CHANNEL_CLIENT_TIMEOUT):
                    response = await self.client.read_json()
                self.response = response
                self.response_queue.put_nowait(response)
            except asyncio.TimeoutError:
                pass
            except (asyncio.IncompleteReadError, ConnectionError):
                break
            finally:
                await asyncio.sleep(SIDE_CHANNEL_CLIENT_SLEEP)
