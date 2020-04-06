"""Implements CSC classes for the TunableLaser.

"""
import traceback
from .component import LaserComponent
from lsst.ts import salobj
import asyncio
import enum
import pathlib


class LaserDetailedState(enum.IntEnum):
    """An enumeration class for handling the TunableLaser's substates.

    These enumerations listed here correspond to the ones found in the
    detailedState enum located in ts_xml under the TunableLaser folder within
    the TunableLaser_Events.xml.

    Attributes
    ----------

    NONPROPAGATING : `int`
        Corresponds to the nonpropgating state.
    PROPAGATINGSTATE : `int`
        Corresponds to the propagating state.

    """
    NONPROPAGATING = 1
    PROPAGATING = 2


class LaserErrorCode(enum.IntEnum):
    """Laser error codes
    """
    ascii_error = 7301
    general_error = 7302
    timeout_error = 7303
    hw_cpu_error = 7304


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

    async def telemetry(self):
        """Sends out the TunableLaser's telemetry.

        """
        try:
            while True:
                if self.summary_state is not salobj.State.FAULT:
                    try:
                        self.model.publish()
                    except TimeoutError as te:
                        self.fault()
                        self.evt_errorCode.set_put(
                            errorCode=LaserErrorCode.timeout_error,
                            errorReport=te.msg,
                            traceback=traceback.format_exc())
                    if (self.model._laser.CPU8000.power_register.register_value == "FAULT" or
                        self.model._laser.M_CPU800.power_register.register_value == "FAULT" or
                        self.model._laser.M_CPU800.power_register_2.register_value == "FAULT") \
                       and self.summary_state is not salobj.State.FAULT:
                        self.fault()
                        self.evt_errorCode.set_put(
                            errorCode=LaserErrorCode.hw_cpu_error,
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
            self.log.exception(e)
            self.evt_errorCode.set_put(
                errorCode=2,
                errorReport=e.msg,
                traceback=traceback.format_exc())
            if self.summary_state is not salobj.State.FAULT:
                self.fault()

    def assert_substate(self, substates, action):
        """Asserts that the action is happening while in the PropagatingState.

        Parameters
        ----------
        action : `str`
            The name of the command being sent.

        Raises
        ------
        salobj.ExpectedError

        """
        if self.detailed_state not in [LaserDetailedState(substate) for substate in substates]:
            raise salobj.ExpectedError(f"{action} not allowed in state {self.detailed_state!r}")

    async def handle_summary_state(self):
        if self.enabled_or_disabled:
            pass

    async def do_changeWavelength(self, data):
        """Changes the wavelength of the laser.

        Parameters
        ----------
        id_data

        Returns
        -------

        """
        self.assert_enabled("changeWavelength")
        try:
            self.model.change_wavelength(data.wavelength)
        except TimeoutError as te:
            self.fault(code=LaserErrorCode.timeout_error, msg=te.msg)
        except Exception as e:
            self.evt_errorCode(
                errorCode=LaserErrorCode.general_error,
                errorReport=e.msg,
                traceback=traceback.format_exc())
        self.evt_wavelengthChanged.set_put(wavelength=data.wavelength)

    async def do_startPropagateLaser(self, data):
        """Changes the state to the Propagating State of the laser.

        Parameters
        ----------
        id_data

        Returns
        -------

        """
        self.assert_enabled("startPropagateLaser")
        try:
            self.model.run()
        except Exception:
            raise
        self.detailed_state = LaserDetailedState.PROPAGATINGSTATE

    async def do_stopPropagateLaser(self, data):
        """Stops the Propagating State of the laser.

        Parameters
        ----------
        id_data

        Returns
        -------

        """
        self.assert_enabled("stopPropagateLaser")
        self.assert_substate([LaserDetailedState.PROPAGATING], "stopPropagateLaser")
        try:
            self.model.stop()
        except Exception:
            raise
        self.detailed_state = LaserDetailedState.ENABLEDSTATE

    async def do_clearFaultState(self, data):
        """Clears the fault state of the laser by turning the power register
        off.

        Parameters
        ----------
        id_data

        Returns
        -------

        """
        self.model.clear_fault()

    @property
    def detailed_state(self):
        """Returns the current substate of the laser and when it changes
        publishes an event.
        """
        return self._detailed_state

    @detailed_state.setter
    def detailed_state(self, new_sub_state):
        self._detailed_state = LaserDetailedState(new_sub_state)
        self.report_detailed_state()

    def report_detailed_state(self):
        self.evt_detailedState.set_put(detailedState=self.detailed_state)

    async def begin_enable(self, data):
        """A temporary hook that sets up the laser for propagation so that it
        is ready to go.

        Parameters
        ----------
        id_data

        Returns
        -------

        """
        try:
            self.model._laser.MaxiOPG.set_configuration(self.model.csc_configuration.optical_configuration)
            self.model._laser.set_output_energy_level("MAX")
        except TimeoutError as te:
            self.fault(code=LaserErrorCode.timeout_error, report=te.msg)

    async def begin_disable(self, data):
        """

        Parameters
        ----------
        id_data

        Returns
        -------

        """
        if self.model._laser.M_CPU800.power_register_2.register_value == "ON":
            try:
                self.model.stop()
                self.detailed_state = LaserDetailedState(LaserDetailedState.ENABLEDSTATE)
            except TimeoutError as te:
                self.fault(code=LaserErrorCode.timeout_error, report=te.msg)
        self.model.set_output_energy_level("OFF")

    async def end_start(self, data):
        try:
            self.model.connect()
            self.telemetry_task = asyncio.ensure_future(self.telemetry())
        except Exception:
            raise

    async def end_standby(self, data):
        try:
            if not self.telemetry_task.done():
                self.telemetry_task.set_result('done')
            self.model.disconnect()
        except Exception:
            raise

    async def configure(self, config):
        try:
            self.log.debug(config)
            self.model.set_configuration(config)
        except Exception as e:
            self.fault(code=LaserErrorCode.general_error, report=e.msg)
            raise

    @staticmethod
    def get_config_pkg():
        return "ts_config_mtcalsys"
