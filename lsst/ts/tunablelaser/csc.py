"""Implements CSC classes for the TunableLaser.

"""
import logging
import traceback
from .component import LaserComponent
from lsst.ts import salobj
import SALPY_TunableLaser
import asyncio
import enum


class LaserDetailedState(enum.IntEnum):
    """An enumeration class for handling the TunableLaser's substates.

    These enumerations listed here correspond to the ones found in the detailedState enum located in ts_xml
    under the TunableLaser folder within the TunableLaser_Events.xml.

    Attributes
    ----------
    DISABLEDSTATE : `int`
        Corresponds to the disabled state.
    ENABLEDSTATE : `int`
        Corresponds to the enabled state.
    FAULTSTATE : `int`
        Corresponds to the fault state.
    OFFLINESTATE : `int`
        Corresponds to the offline state.
    STANDBYSTATE : `int`
        Corresponds to the standby state.
    PROPAGATINGSTATE : `int`
        Corresponds to the propagating state.

    """
    DISABLEDSTATE = SALPY_TunableLaser.TunableLaser_shared_DetailedState_DisabledState
    ENABLEDSTATE = SALPY_TunableLaser.TunableLaser_shared_DetailedState_EnabledState
    FAULTSTATE = SALPY_TunableLaser.TunableLaser_shared_DetailedState_FaultState
    OFFLINESTATE = SALPY_TunableLaser.TunableLaser_shared_DetailedState_OfflineState
    STANDBYSTATE = SALPY_TunableLaser.TunableLaser_shared_DetailedState_StandbyState
    PROPAGATINGSTATE = SALPY_TunableLaser.TunableLaser_shared_DetailedState_PropagatingState


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
        The initial state that a CSC will start up in. Only useful for unit tests as most CSCs
        will start in `salobj.State.STANDBY`

    Attributes
    ----------
    model : `LaserModel`
        The model of the laser component which handles the actual hardware.
    frequency : `float`
        The amount of time that telemetry waits to publish.
    wavelength_topic
    temperature_topic

    """
    def __init__(self,frequency=1, initial_state=salobj.State.STANDBY,index=None,schema="/home/ecoughlin/gitrepo/ts_laser/schema/TunableLaser.yaml"):
        super().__init__(SALPY_TunableLaser,index,schema)
        self._detailed_state = LaserDetailedState.STANDBYSTATE
        self.model = LaserModel()
        self.frequency = frequency
        self.wavelength_topic = self.tel_wavelength.DataType()
        self.temperature_topic = self.tel_temperature.DataType()
        self.summary_state = initial_state

    async def telemetry(self):
        """Sends out the TunableLaser's telemetry.

        Returns
        -------
        None

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
                    if (self.model._laser.CPU8000.power_register.register_value == "FAULT" or \
                        self.model._laser.M_CPU800.power_register.register_value == "FAULT" or \
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

    def assert_propagating(self, action):
        """Asserts that the action is happening while in the PropagatingState.

        Parameters
        ----------
        action : `str`
            The name of the command being sent.

        Raises
        ------
        salobj.ExpectedError

        Returns
        -------
        None

        """
        if self.detailed_state != LaserDetailedState.PROPAGATINGSTATE:
            raise salobj.ExpectedError(f"{action} not allowed in state {self.detailed_state}")

    async def do_changeWavelength(self, id_data):
        """Changes the wavelength of the laser.

        Parameters
        ----------
        id_data

        Returns
        -------

        """
        self.assert_enabled("changeWavelength")
        try:
            self.model.change_wavelength(id_data.data.wavelength)
        except TimeoutError as te:
            self.fault(code=LaserErrorCode.timeout_error,msg=te.msg)
        except Exception as e:
            self.evt_errorCode(
                errorCode=LaserErrorCode.general_error,
                errorReport=e.msg,
                traceback=traceback.format_exc())
        wavelength_changed_topic = self.evt_wavelengthChanged.DataType()
        wavelength_changed_topic.wavelength = id_data.data.wavelength
        self.evt_wavelengthChanged.put(wavelength_changed_topic)

    async def do_startPropagateLaser(self, id_data):
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
        except Exception as e:
            raise
        self.detailed_state = LaserDetailedState.PROPAGATINGSTATE

    async def do_stopPropagateLaser(self, id_data):
        """Stops the Propagating State of the laser.

        Parameters
        ----------
        id_data

        Returns
        -------

        """
        self.assert_enabled("stopPropagateLaser")
        self.assert_propagating("stopPropagateLaser")
        try:
            self.model.stop()
        except Exception as e:
            raise
        self.detailed_state = LaserDetailedState.ENABLEDSTATE

    async def do_abort(self, id_data):
        """Actually does nothing and is not implemented yet.

        Parameters
        ----------
        id_data

        Returns
        -------

        """
        pass

    async def do_clearFaultState(self, id_data):
        """Clears the fault state of the laser by turning the power register off.

        Parameters
        ----------
        id_data

        Returns
        -------

        """
        self.model._laser.clear_fault()

    async def do_setValue(self, id_data):
        """Actually does nothing and is not implemented yet.

        Parameters
        ----------
        id_data

        Returns
        -------

        """
        pass

    async def do_enterControl(self, id_data):
        """Does nothing because it is not implemented. It also is not necessary for the use of this laser.

        Parameters
        ----------
        id_data

        Returns
        -------

        """
        pass

    @property
    def detailed_state(self):
        """Returns the current substate of the laser and when it changes publishes an event.
        """
        return self._detailed_state

    @detailed_state.setter
    def detailed_state(self, new_sub_state):
        self._detailed_state = LaserDetailedState(new_sub_state)
        detailed_state_topic = self.evt_detailedState.DataType()
        detailed_state_topic.detailedState = self._detailed_state
        self.evt_detailedState.put(detailed_state_topic)

    async def begin_enable(self, id_data):
        """A temporary hook that sets up the laser for propagation so that it is ready to go.

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
            self.fault(code=LaserErrorCode.timeout_error,report=te.msg)

    async def begin_disable(self, id_data):
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
                self.fault(code=LaserErrorCode.timeout_error,report=te.msg)
        self.model.set_output_energy_level("OFF")

    def end_start(self,id_data):
        try:
            self.model.connect()
            self.telemetry_task=asyncio.ensure_future(self.telemetry())
        except Exception as e:
            raise

    def end_standby(self,id_data):
        try:
            if not self.telemetry_task.done():
                self.telemetry_task.set_result('done')
            self.model.disconnect()
        except Exception as e:
            raise

    def configure(self,config):
        try:
            self.log.debug(config)
            self.model.set_configuration(config)
        except Exception as e:
            self.fault(code=LaserErrorCode.general_error,report=e.msg)
            raise

    def get_config_pkg(self):
        return "ts_config_mttcs"

    async def implement_simulation_mode(self, simulation_mode):
        self.log.debug(simulation_mode)
        if (simulation_mode == 0) or (simulation_mode is None):
            self.model._laser.set_simulation_mode(False)
        elif simulation_mode == 1:
            self.model._laser.set_simulation_mode(True)
        else:
            raise salobj.ExpectedError("no")


class LaserModel:
    """This is the model class for the MVC paradigm.

    """
    def __init__(self):
        self._laser = LaserComponent()

    def change_wavelength(self, wavelength):
        """Changes the wavelength of the laser.

        Parameters
        ----------
        wavelength

        Returns
        -------
        None

        """
        self._laser.MaxiOPG.change_wavelength(wavelength=wavelength)

    def set_output_energy_level(self, output_energy_level):
        self._laser.set_output_energy_level(output_energy_level)

    def run(self):
        """Propagates the laser.

        Returns
        -------
        None

        """
        self._laser.start_propagating()

    def stop(self):
        """Stops propagating the laser.

        Returns
        -------
        None

        """
        self._laser.stop_propagating()

    def publish(self):
        """Updates the laser's attributes.

        Returns
        -------
        None

        """
        self._laser.publish()

    def set_configuration(self, config):
        self.csc_configuration = config
        self._laser.configuration = self.csc_configuration
        self._laser.set_configuration()

    def connect(self):
        self._laser.connect()

    def disconnect(self):
        self._laser.disconnect()
