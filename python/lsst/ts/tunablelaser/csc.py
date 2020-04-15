"""Implements CSC classes for the TunableLaser.

"""
from .component import LaserComponent
from lsst.ts import salobj
import asyncio
import pathlib
from lsst.ts.idl.enums import TunableLaser


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
    model : `LaserModel`
        The model of the laser component which handles the actual hardware.

    """
    def __init__(self, index,
                 initial_state=salobj.State.STANDBY, config_dir=None, initial_simulation_mode=0):
        schema_path = pathlib.Path(__file__).resolve().parents[4].joinpath("schema", "TunableLaser.yaml")
        super().__init__(name="TunableLaser", index=index, schema_path=schema_path, config_dir=config_dir,
                         initial_state=initial_state, initial_simulation_mode=initial_simulation_mode)
        self.model = LaserComponent()
        self.evt_detailedState.set_put(detailedState=TunableLaser.DetailedState.NONPROPAGATING)

    async def telemetry(self):
        """Send out the TunableLaser's telemetry.

        """
        try:
            while True:
                if self.summary_state is not salobj.State.FAULT:
                    try:
                        self.model.publish()
                    except TimeoutError:
                        self.fault(code=TunableLaser.LaserErrorCode.timeout_error)
                    if (self.model.CPU8000.power_register.register_value == "FAULT"
                        or self.model.M_CPU800.power_register.register_value == "FAULT"
                        or self.model.M_CPU800.power_register_2.register_value == "FAULT") \
                       and self.summary_state is not salobj.State.FAULT:
                        self.fault(code=TunableLaser.LaserErrorCode.hw_cpu_error,
                                   report=(f"Code:{self.CPU8000.fault_register.fault}"
                                           f" Code:{self.M_CPU800.fault_register.fault}"
                                           f" Code:{self.M_CPU800.fault_register_2.fault}"))
                    if self.summary_state is not salobj.State.FAULT:
                        self.wavelength_topic.wavelength = float(
                            self.model.MaxiOPG.wavelength_register.register_value)
                        self.temperature_topic.tk6_temperature = float(
                            self.model.TK6.display_temperature_register.register_value)
                        self.temperature_topic.tk6_temperature_2 = float(
                            self.model.TK6.display_temperature_register_2.register_value)
                        self.temperature_topic.ldco48bp_temperature = float(
                            self.model.LDCO48BP.display_temperature_register.register_value)
                        self.temperature_topic.ldco48bp_temperature_2 = float(
                            self.model.LDCO48BP.display_temperature_register_2.register_value)
                        self.temperature_topic.ldco48bp_temperature_3 = float(
                            self.model.LDCO48BP.display_temperature_register_3.register_value)
                        self.temperature_topic.m_ldco48_temperature = float(
                            self.model.M_LDCO48.display_temperature_register.register_value
                        )
                        self.temperature_topic.m_ldco48_temperature_2 = float(
                            self.model.M_LDCO48.display_temperature_register_2.register_value
                        )
                        self.tel_wavelength.put(self.wavelength_topic)
                        self.tel_temperature.put(self.temperature_topic)
                await asyncio.sleep(self.frequency)
        except Exception:
            if self.summary_state is not salobj.State.FAULT:
                self.fault(code=TunableLaser.LaserErrorCode.hw_cpu_error, report=f"Problem with hardware.")

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
        if self.detailed_state not in [TunableLaser.LaserDetailedState(substate) for substate in substates]:
            raise salobj.ExpectedError(f"{action} not allowed in state {self.detailed_state!r}")

    async def handle_summary_state(self):
        if self.enabled_or_disabled:
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
        try:
            self.model.change_wavelength(data.wavelength)
        except TimeoutError as te:
            self.fault(code=TunableLaser.LaserErrorCode.timeout_error, msg=te.msg)
        self.evt_wavelengthChanged.set_put(wavelength=data.wavelength)

    async def do_startPropagateLaser(self, data):
        """Change the state to the Propagating State of the laser.

        Parameters
        ----------
        data
        """
        self.assert_enabled("startPropagateLaser")
        self.assert_substate([TunableLaser.LaserDetailedState.NONPROPAGATING], "startPropagateLaser")
        try:
            self.model.MaxiOPG.set_configuration(self.model.csc_configuration.optical_configuration)
            self.model.set_output_energy_level("MAX")
            self.model.start_propagating()
        except TimeoutError as te:
            self.fault(code=TunableLaser.LaserErrorCode.timeout_error, report=te.msg)
        self.detailed_state = TunableLaser.LaserDetailedState.PROPAGATINGSTATE

    async def do_stopPropagateLaser(self, data):
        """Stop the Propagating State of the laser.

        Parameters
        ----------
        data
        """
        self.assert_enabled("stopPropagateLaser")
        self.assert_substate([TunableLaser.LaserDetailedState.PROPAGATING], "stopPropagateLaser")
        self.model.stop_propagating()
        self.detailed_state = TunableLaser.LaserDetailedState.NONPROPAGATING

    async def do_clearFaultState(self, data):
        """Clear the hardware fault state of the laser by turning the power
        register off.

        Parameters
        ----------
        data
        """
        self.model.clear_fault()

    @property
    def detailed_state(self):
        """Return the current substate of the laser and when it changes
        publishes an event.
        """
        return TunableLaser.LaserDetailedState(self.evt_detailedState.data.detailedState)

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
