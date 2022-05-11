"""Implements CSC classes for the TunableLaser.

"""

import asyncio

from lsst.ts import salobj
from lsst.ts.idl.enums import TunableLaser
from lsst.ts import tcpip
from lsst.ts import utils

from . import __version__
from .component import LaserComponent
from .config_schema import CONFIG_SCHEMA
from .mock_server import MockServer


class LaserCSC(salobj.ConfigurableCsc):
    """This is the class that implements the TunableLaser CSC.

    Parameters
    ----------
    address : `str`
        The physical usb port string where the laser is located.
    frequency : `float`, optional
        The amount of time that the telemetry stream is published.
    initial_state : `lsst.ts.salobj.State`, optional
        The initial state that a CSC will start up in. Only useful for unit
        tests as most CSCs will start in `salobj.State.STANDBY`

    Attributes
    ----------
    model : `LaserComponent`
        The model of the laser component which handles the actual hardware.
    telemetry_rate : `float`
    telemetry_task : `asyncio.Future`
    simulator : `MockServer`

    """

    valid_simulation_modes = (0, 1)
    version = __version__

    def __init__(
        self,
        initial_state=salobj.State.STANDBY,
        config_dir=None,
        simulation_mode=0,
    ):
        super().__init__(
            name="TunableLaser",
            config_schema=CONFIG_SCHEMA,
            index=None,
            config_dir=config_dir,
            initial_state=initial_state,
            simulation_mode=simulation_mode,
        )
        self.model = LaserComponent(bool(simulation_mode))
        self.telemetry_rate = 0.5
        self.telemetry_task = utils.make_done_future()
        self.simulator = None

    @property
    def connected(self):
        if self.model.commander is None:
            return False
        return self.model.commander.connected

    async def telemetry(self):
        """Send out the TunableLaser's telemetry."""
        while True:
            try:
                self.log.debug("Telemetry updating")
                await self.model.read_all_registers()
                self.log.debug(f"model={self.model}")
                self.log.debug(
                    f"detailed_state={self.evt_detailedState.data.detailedState}"
                )
                if (
                    self.model.cpu8000.power_register.register_value == "FAULT"
                    or self.model.m_cpu800.power_register.register_value == "FAULT"
                    or self.model.m_cpu800.power_register_2.register_value == "FAULT"
                ):
                    self.fault(
                        code=TunableLaser.LaserErrorCode.HW_CPU_ERROR,
                        report=(
                            f"Code:{self.model.cpu8000.fault_register.fault}"
                            f" Code:{self.model.m_cpu800.fault_register.fault}"
                            f" Code:{self.model.m_cpu800.fault_register_2.fault}"
                        ),
                    )
                await self.tel_wavelength.set_write(
                    wavelength=float(
                        self.model.maxi_opg.wavelength_register.register_value
                    )
                )
                await self.tel_temperature.set_write(
                    tk6_temperature=float(
                        self.model.tk6.display_temperature_register.register_value
                    ),
                    tk6_temperature_2=float(
                        self.model.tk6.display_temperature_register_2.register_value
                    ),
                    ldco48bp_temperature=float(
                        self.model.ldco48bp.display_temperature_register.register_value
                    ),
                    ldco48bp_temperature_2=float(
                        self.model.ldco48bp.display_temperature_register_2.register_value
                    ),
                    ldco48bp_temperature_3=float(
                        self.model.ldco48bp.display_temperature_register_3.register_value
                    ),
                    m_ldco48_temperature=float(
                        self.model.m_ldcO48.display_temperature_register.register_value
                    ),
                    m_ldco48_temperature_2=float(
                        self.model.m_ldcO48.display_temperature_register_2.register_value
                    ),
                )
                self.log.debug("Telemetry updated")
            except asyncio.CancelledError:
                self.log.info("Telemetry loop cancelled.")
                return
            except Exception:
                self.log.exception("Telemetry loop failed.")
                raise
            await asyncio.sleep(self.telemetry_rate)

    def assert_substate(self, substates, action):
        """Assert that the action is happening while in the PropagatingState.

        Parameters
        ----------
        substates : `list`
            A list of allowed states
        action : `str`
            The name of the command being sent.

        Raises
        ------
        salobj.ExpectedError
            Raised when an action is not allowed in a substate.

        """
        if self.evt_detailedState.data.detailedState not in [
            TunableLaser.LaserDetailedState(substate) for substate in substates
        ]:
            raise salobj.ExpectedError(
                f"{action} not allowed in state {self.detailed_state!r}"
            )

    async def handle_summary_state(self):
        if self.disabled_or_enabled:
            if self.simulation_mode:
                if self.simulator is None:
                    self.simulator = MockServer()
                    await self.simulator.start_task
                    await self.model.disconnect()
                host = tcpip.LOCAL_HOST
                port = self.simulator.port
            else:
                host = self.model.config.host
                port = self.model.config.port
            if not self.connected:
                await self.evt_detailedState.set_write(
                    detailedState=TunableLaser.LaserDetailedState.NONPROPAGATING
                )
                await self.model.connect(host, port)
                await self.model.maxi_opg.set_configuration(
                    self.model.maxi_opg.optical_alignment
                )
            if self.telemetry_task.done():
                self.telemetry_task = asyncio.create_task(self.telemetry())
        else:
            if self.model.is_propgating:
                await self.model.stop_propagating()
            if self.simulator is not None:
                await self.simulator.close()
                self.simulator = None
            await self.model.disconnect()
            self.telemetry_task.cancel()

    async def do_changeWavelength(self, data):
        """Change the wavelength of the laser.

        Parameters
        ----------
        data
        """
        self.assert_enabled("changeWavelength")
        await self.model.change_wavelength(data.wavelength)
        await self.evt_wavelengthChanged.set_write(wavelength=data.wavelength)

    async def do_startPropagateLaser(self, data):
        """Change the state to the Propagating State of the laser.

        Parameters
        ----------
        data
        """
        self.assert_enabled("startPropagateLaser")
        self.assert_substate(
            [TunableLaser.LaserDetailedState.NONPROPAGATING], "startPropagateLaser"
        )
        await self.model.set_output_energy_level("MAX")
        await self.model.start_propagating()
        await self.publish_new_detailed_state(
            TunableLaser.LaserDetailedState.PROPAGATING
        )

    async def do_stopPropagateLaser(self, data):
        """Stop the Propagating State of the laser.

        Parameters
        ----------
        data
        """
        self.assert_enabled("stopPropagateLaser")
        self.assert_substate(
            [TunableLaser.LaserDetailedState.PROPAGATING], "stopPropagateLaser"
        )
        await self.model.stop_propagating()
        await self.publish_new_detailed_state(
            TunableLaser.LaserDetailedState.NONPROPAGATING
        )

    async def do_clearLaserFault(self, data):
        """Clear the hardware fault state of the laser by turning the power
        register off.

        Parameters
        ----------
        data
        """
        self.assert_enabled("clearFaultState")
        await self.model.clear_fault()

    async def publish_new_detailed_state(self, new_sub_state):
        new_sub_state = TunableLaser.LaserDetailedState(new_sub_state)
        await self.evt_detailedState.set_write(detailedState=new_sub_state)

    async def configure(self, config):
        """Configure the CSC."""
        self.log.debug(f"config={config}")
        await self.model.set_configuration(config)

    @staticmethod
    def get_config_pkg():
        """Return the configuration package name."""
        return "ts_config_mtcalsys"

    async def close_tasks(self):
        await super().close_tasks()
        self.telemetry_task.cancel()
        if self.simulator is not None:
            await self.simulator.close()
            self.simulator = None
        await self.model.disconnect()
