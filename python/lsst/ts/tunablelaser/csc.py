"""Implements CSC classes for the TunableLaser.

"""

import asyncio
import pathlib

from lsst.ts import salobj
from lsst.ts.idl.enums import TunableLaser

from .component import LaserComponent


class LaserCSC(salobj.ConfigurableCsc):
    """This is the class that implements the TunableLaser CSC.

    Parameters
    ----------
    address : `str`
        The physical usb port string where the laser is located.
    frequency : `float`, optional
        The amount of time that the telemetry stream is published.
    initial_state : `salobj.State`, optional
        The initial state that a CSC will start up in. Only useful for unit
        tests as most CSCs will start in `salobj.State.STANDBY`

    Attributes
    ----------
    model : `LaserComponent`
        The model of the laser component which handles the actual hardware.

    """

    valid_simulation_modes = (0, 1)

    def __init__(
        self, initial_state=salobj.State.STANDBY, config_dir=None, simulation_mode=0,
    ):
        schema_path = (
            pathlib.Path(__file__)
            .resolve()
            .parents[4]
            .joinpath("schema", "TunableLaser.yaml")
        )
        super().__init__(
            name="TunableLaser",
            schema_path=schema_path,
            index=None,
            config_dir=config_dir,
            initial_state=initial_state,
            simulation_mode=simulation_mode,
        )
        self.model = LaserComponent(bool(simulation_mode))
        self.evt_detailedState.set_put(
            detailedState=TunableLaser.LaserDetailedState.NONPROPAGATING
        )
        self.telemetry_rate = 1
        self.telemetry_task = salobj.make_done_future()

    async def telemetry(self):
        """Send out the TunableLaser's telemetry.

        """
        while True:
            self.log.debug("Telemetry updating")
            self.model.publish()
            self.log.debug(self.model)
            self.log.debug(self.detailed_state)
            if (
                self.model.CPU8000.power_register.register_value == "FAULT"
                or self.model.M_CPU800.power_register.register_value == "FAULT"
                or self.model.M_CPU800.power_register_2.register_value == "FAULT"
            ):
                self.fault(
                    code=TunableLaser.LaserErrorCode.HW_CPU_ERROR,
                    report=(
                        f"Code:{self.CPU8000.fault_register.fault}"
                        f" Code:{self.M_CPU800.fault_register.fault}"
                        f" Code:{self.M_CPU800.fault_register_2.fault}"
                    ),
                )
            self.tel_wavelength.set_put(
                wavelength=float(self.model.MaxiOPG.wavelength_register.register_value)
            )
            self.tel_temperature.set_put(
                tk6_temperature=float(
                    self.model.TK6.display_temperature_register.register_value
                ),
                tk6_temperature_2=float(
                    self.model.TK6.display_temperature_register_2.register_value
                ),
                ldco48bp_temperature=float(
                    self.model.LDCO48BP.display_temperature_register.register_value
                ),
                ldco48bp_temperature_2=float(
                    self.model.LDCO48BP.display_temperature_register_2.register_value
                ),
                ldco48bp_temperature_3=float(
                    self.model.LDCO48BP.display_temperature_register_3.register_value
                ),
                m_ldco48_temperature=float(
                    self.model.M_LDCO48.display_temperature_register.register_value
                ),
                m_ldco48_temperature_2=float(
                    self.model.M_LDCO48.display_temperature_register_2.register_value
                ),
            )
            self.log.debug("Telemetry updated")
            # raise Exception("Intentional exception.")
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
        if self.detailed_state not in [
            TunableLaser.LaserDetailedState(substate) for substate in substates
        ]:
            raise salobj.ExpectedError(
                f"{action} not allowed in state {self.detailed_state!r}"
            )

    async def handle_summary_state(self):
        if self.disabled_or_enabled:
            if not self.model.connected:
                self.model.connect()
            if self.telemetry_task.done():
                self.telemetry_task = asyncio.create_task(self.telemetry())
        else:
            if self.model.is_propgating:
                self.model.stop_propagating()
            self.model.disconnect()
            self.telemetry_task.cancel()

    async def do_changeWavelength(self, data):
        """Change the wavelength of the laser.

        Parameters
        ----------
        data
        """
        self.assert_enabled("changeWavelength")
        self.model.change_wavelength(data.wavelength)
        self.evt_wavelengthChanged.set_put(wavelength=data.wavelength)

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
        self.model.MaxiOPG.set_configuration(self.model.MaxiOPG.optical_alignment)
        self.model.set_output_energy_level("MAX")
        self.model.start_propagating()
        self.detailed_state = TunableLaser.LaserDetailedState.PROPAGATING

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
        self.model.stop_propagating()
        self.detailed_state = TunableLaser.LaserDetailedState.NONPROPAGATING

    async def do_clearFaultState(self, data):
        """Clear the hardware fault state of the laser by turning the power
        register off.

        Parameters
        ----------
        data
        """
        self.assert_enabled("clearFaultState")
        self.model.clear_fault()

    @property
    def detailed_state(self):
        """Return the current substate of the laser and when it changes
        publishes an event.
        """
        return TunableLaser.LaserDetailedState(
            self.evt_detailedState.data.detailedState
        )

    @detailed_state.setter
    def detailed_state(self, new_sub_state):
        new_sub_state = TunableLaser.LaserDetailedState(new_sub_state)
        self.evt_detailedState.set_put(detailedState=new_sub_state)

    async def configure(self, config):
        self.log.debug(f"config={config}")
        self.model.set_configuration(config)

    @staticmethod
    def get_config_pkg():
        return "ts_config_mtcalsys"

    async def close_tasks(self):
        await super().close_tasks()
        self.telemetry_task.cancel()
        self.model.disconnect()
