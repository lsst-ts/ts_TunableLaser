"""Implements CSC classes for the TunableLaser.

"""
import traceback
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
                    except TimeoutError as te:
                        self.fault()
                        self.evt_errorCode.set_put(
                            errorCode=TunableLaser.LaserErrorCode.timeout_error,
                            errorReport=te.msg,
                            traceback=traceback.format_exc())
                    if (self.model._laser.CPU8000.power_register.register_value == "FAULT"
                        or self.model._laser.M_CPU800.power_register.register_value == "FAULT"
                        or self.model._laser.M_CPU800.power_register_2.register_value == "FAULT") \
                       and self.summary_state is not salobj.State.FAULT:
                        self.fault()
                        self.evt_errorCode.set_put(
                            errorCode=TunableLaser.LaserErrorCode.hw_cpu_error,
                            errorReport=f"Code:{self._laser.CPU8000.fault_register.fault}"
                            f" Code:{self._laser.M_CPU800.fault_register.fault}"
                            f" Code:{self._laser.M_CPU800.fault_register_2.fault}",
                            traceback="")
                    if self.summary_state is not salobj.State.FAULT:
                        self.wavelength_topic.wavelength = float(
                            self.model._laser.MaxiOPG.wavelength_register.register_value)
                        self.temperature_topic.tk6_temperature = float(
                            self.model._laser.TK6.display_temperature_register.register_value)
                        self.temperature_topic.tk6_temperature_2 = float(
                            self.model._laser.TK6.display_temperature_register_2.register_value)
                        self.temperature_topic.ldco48bp_temperature = float(
                            self.model._laser.LDCO48BP.display_temperature_register.register_value)
                        self.temperature_topic.ldco48bp_temperature_2 = float(
                            self.model._laser.LDCO48BP.display_temperature_register_2.register_value)
                        self.temperature_topic.ldco48bp_temperature_3 = float(
                            self.model._laser.LDCO48BP.display_temperature_register_3.register_value)
                        self.temperature_topic.m_ldco48_temperature = float(
                            self.model._laser.M_LDCO48.display_temperature_register.register_value
                        )
                        self.temperature_topic.m_ldco48_temperature_2 = float(
                            self.model._laser.M_LDCO48.display_temperature_register_2.register_value
                        )
                        self.tel_wavelength.put(self.wavelength_topic)
                        self.tel_temperature.put(self.temperature_topic)
                await asyncio.sleep(self.frequency)
        except Exception as e:
            self.evt_errorCode.set_put(
                errorCode=2,
                errorReport=e.msg,
                traceback=traceback.format_exc())
            if self.summary_state is not salobj.State.FAULT:
                self.fault(code=TunableLaser.LaserErrorCode.hw_cpu_error, reason=f"Problem with hardware.")

    def assert_substate(self, substates, action):
        """Assert that the action is happening while in the PropagatingState.

        Parameters
        ----------
        action : `str`
            The name of the command being sent.

        Raises
        ------
        salobj.ExpectedError

        """
        if self.detailed_state not in [TunableLaser.LaserDetailedState(substate) for substate in substates]:
            raise salobj.ExpectedError(f"{action} not allowed in state {self.detailed_state!r}")

    async def handle_summary_state(self):
        if self.enabled_or_disabled:
            pass

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
        except Exception as e:
            self.evt_errorCode(
                errorCode=TunableLaser.LaserErrorCode.general_error,
                errorReport=e.msg,
                traceback=traceback.format_exc())
        self.evt_wavelengthChanged.set_put(wavelength=data.wavelength)

    async def do_startPropagateLaser(self, data):
        """Change the state to the Propagating State of the laser.

        Parameters
        ----------
        data
        """
        self.assert_enabled("startPropagateLaser")
        try:
            self.model.run()
        except Exception as e:
            self.evt_errorCode(
                errorCode=TunableLaser.LaserErrorCode.general_error,
                errorReport=e.msg,
                traceback=traceback.format_exc()
            )
        self.detailed_state = TunableLaser.LaserDetailedState.PROPAGATINGSTATE

    async def do_stopPropagateLaser(self, data):
        """Stop the Propagating State of the laser.

        Parameters
        ----------
        data
        """
        self.assert_enabled("stopPropagateLaser")
        self.assert_substate([TunableLaser.LaserDetailedState.PROPAGATING], "stopPropagateLaser")
        try:
            self.model.stop()
        except Exception as e:
            self.evt_errorCode(
                errorCode=TunableLaser.LaserErrorCode.general_error,
                errorReport=e.msg,
                traceback=traceback.format_exc()
            )
        self.detailed_state = TunableLaser.LaserDetailedState.ENABLEDSTATE

    async def do_clearFaultState(self, data):
        """Clear the fault state of the laser by turning the power register
        off.

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

    async def begin_enable(self, data):
        """A hook that sets up the laser for propagation so that it
        is ready to go.

        Parameters
        ----------
        data
        """
        try:
            self.model._laser.MaxiOPG.set_configuration(self.model.csc_configuration.optical_configuration)
            self.model._laser.set_output_energy_level("MAX")
        except TimeoutError as te:
            self.fault(code=TunableLaser.LaserErrorCode.timeout_error, report=te.msg)

    async def begin_disable(self, data):
        """

        Parameters
        ----------
        data
        """
        if self.model._laser.M_CPU800.power_register_2.register_value == "ON":
            try:
                self.model.stop()
                self.detailed_state = TunableLaser.LaserDetailedState(
                    TunableLaser.LaserDetailedState.ENABLEDSTATE)
            except TimeoutError as te:
                self.fault(code=TunableLaser.LaserErrorCode.timeout_error, report=te.msg)
        self.model.set_output_energy_level("OFF")

    async def end_start(self, data):
        try:
            self.model.connect()
            self.telemetry_task = asyncio.ensure_future(self.telemetry())
        except Exception as e:
            self.evt_errorCode(
                errorCode=TunableLaser.LaserErrorCode.general_error,
                errorReport=e.msg,
                traceback=traceback.format_exc()
            )

    async def end_standby(self, data):
        try:
            if not self.telemetry_task.done():
                self.telemetry_task.set_result('done')
            self.model.disconnect()
        except Exception as e:
            self.evt_errorCode(
                errorCode=TunableLaser.LaserErrorCode.general_error,
                errorReport=e.msg,
                traceback=traceback.format_exc()
            )

    async def configure(self, config):
        try:
            self.log.debug(f"config={config}")
            self.model.set_configuration(config)
        except Exception as e:
            self.log.exception("set_configuration failed.")
            self.fault(code=TunableLaser.LaserErrorCode.general_error, report=e.msg)
            self.evt_errorCode(
                errorCode=TunableLaser.LaserErrorCode.general_error,
                errorReport=e.msg,
                traceback=traceback.format_exc()
            )

    @staticmethod
    def get_config_pkg():
        return "ts_config_mtcalsys"
