"""Implements CSC classes for the TunableLaser.

"""
import logging
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
    DISABLEDSTATE: int
        Corresponds to the disabled state.
    ENABLEDSTATE: int
        Corresponds to the enabled state.
    FAULTSTATE: int
        Corresponds to the fault state.
    OFFLINESTATE: int
        Corresponds to the offline state.
    STANDBYSTATE: int
        Corresponds to the standby state.
    PROPAGATINGSTATE: int
        Corresponds to the propagating state.

    """
    DISABLEDSTATE = 1
    ENABLEDSTATE = 2
    FAULTSTATE = 3
    OFFLINESTATE = 4
    STANDBYSTATE = 5
    PROPAGATINGSTATE = 6


class LaserCSC(salobj.BaseCsc):
    """This is the class that implements the TunableLaser CSC.

    Parameters
    ----------
    address: str
        The physical usb port string where the laser is located.
    frequency: float, optional
        The amount of time that the telemetry stream is published.
    initial_state: salobj.State, optional
        The initial state that a CSC will start up in. Only useful for unit tests as most CSCs
        will start in `State.STANDBY`

    Attributes
    ----------
    model: LaserModel
        The model of the laser component which handles the actual hardware.
    frequency: float
        The amount of time that telemetry waits to publish.
    wavelength_topic
    temperature_topic

    """
    def __init__(self, address, configuration, frequency=1, initial_state=salobj.State.STANDBY):
        super().__init__(SALPY_TunableLaser)
        self._detailed_state = LaserDetailedState.STANDBYSTATE
        self.model = LaserModel(port=address, configuration=configuration)
        self.frequency = frequency
        self.wavelength_topic = self.tel_wavelength.DataType()
        self.temperature_topic = self.tel_temperature.DataType()
        self.summary_state = initial_state
        asyncio.ensure_future(self.telemetry())

    async def telemetry(self):
        """Sends out the TunableLaser's telemetry.

        Returns
        -------
        None

        """
        while True:
            try:
                self.model.publish()
            except TimeoutError as te:
                self.fault()
            if self.model._laser.CPU8000.power_register.register_value == "FAULT" or \
                    self.model._laser.M_CPU800.power_register.register_value == "FAULT" or \
                    self.model._laser.M_CPU800.power_register_2.register_value == "FAULT" \
                    and self.summary_state is not salobj.State.FAULT:
                self.fault()
            self.wavelength_topic.wavelength = float(
                self.model._laser.MaxiOPG.wavelength_register.register_value[:-2])
            self.temperature_topic.tk6_temperature = float(
                self.model._laser.TK6.display_temperature_register.register_value[:-1])
            self.temperature_topic.tk6_temperature_2 = float(
                self.model._laser.TK6.display_temperature_register_2.register_value[:-1])
            self.temperature_topic.ldco48bp_temperature = float(
                self.model._laser.LDCO48BP.display_temperature_register.register_value[:-1])
            self.temperature_topic.ldco48bp_temperature_2 = float(
                self.model._laser.LDCO48BP.display_temperature_register_2.register_value[:-1])
            self.temperature_topic.ldco48bp_temperature_3 = float(
                self.model._laser.LDCO48BP.display_temperature_register_3.register_value[:-1])
            self.temperature_topic.m_ldco48_temperature = float(
                self.model._laser.M_LDCO48.display_temperature_register.register_value[:-1]
            )
            self.temperature_topic.m_ldco48_temperature_2 = float(
                self.model._laser.M_LDCO48.display_temperature_register_2.register_value[:-1]
            )
            self.tel_wavelength.put(self.wavelength_topic)
            self.tel_temperature.put(self.temperature_topic)
            await asyncio.sleep(self.frequency)

    def assert_propagating(self, action):
        """Asserts that the action is happening while in the PropagatingState.

        Parameters
        ----------
        action: str
            The name of the command being sent.

        Raises
        ------
        ExpectedError

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
            self.fault()
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
        except TimeoutError as te:
            self.fault()
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
        except TimeoutError as te:
            self.fault()
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

    def begin_enable(self, id_data):
        """A temporary hook that sets up the laser for propagation so that it is ready to go.

        Parameters
        ----------
        id_data

        Returns
        -------

        """
        try:
            self.model._laser.MaxiOPG.set_configuration("No SCU")
            self.model._laser.set_output_energy_level("MAX")
        except TimeoutError as te:
            self.fault()

    def begin_disable(self, id_data):
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
                self.fault()


class LaserModel:
    """This is the model class for the MVC paradigm.

    Parameters
    ----------
    port
    simulation_mode

    """
    def __init__(self, port, configuration, simulation_mode=False):
        self._laser = LaserComponent(port=port, configuration=configuration, simulation_mode=simulation_mode)

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


class LaserDeveloperRemote:
    """This is a class for development purposes.

    This class implements a developer remote for sending commands to the standing CSC.

    Attributes
    ----------
    remote: Remote
    log: logging.Logger

    """
    def __init__(self):
        self.remote = salobj.Remote(SALPY_TunableLaser)
        self.log = logging.getLogger(__name__)

    async def standby(self, timeout=10):
        """Standby command

        Parameters
        ----------
        timeout

        Returns
        -------

        """
        standby_topic = self.remote.cmd_standby.DataType()
        standby_ack = await self.remote.cmd_standby.start(standby_topic, timeout=timeout)
        self.log.info(standby_ack.ack.ack)

    async def start(self, timeout=10):
        """Start command

        Parameters
        ----------
        timeout

        Returns
        -------

        """
        start_topic = self.remote.cmd_start.DataType()
        start_ack = await self.remote.cmd_start.start(start_topic, timeout=timeout)
        self.log.info(start_ack.ack.ack)

    async def enable(self, timeout=10):
        """Enable command

        Parameters
        ----------
        timeout

        Returns
        -------

        """
        enable_topic = self.remote.cmd_enable.DataType()
        enable_ack = await self.remote.cmd_enable.start(enable_topic, timeout=timeout)
        self.log.info(enable_ack.ack.ack)

    async def disable(self, timeout=10):
        """Disable command

        Parameters
        ----------
        timeout

        Returns
        -------

        """
        disable_topic = self.remote.cmd_disable.DataType()
        disable_ack = await self.remote.cmd_disable.start(disable_topic, timeout=timeout)
        self.log.info(disable_ack.ack.ack)

    async def change_wavelength(self, wavelength, timeout=10):
        """

        Parameters
        ----------
        wavelength
        timeout

        Returns
        -------

        """
        change_wavelength_topic = self.remote.cmd_changeWavelength.DataType()
        change_wavelength_topic.wavelength = float(wavelength)
        change_wavelength_ack = await self.remote.cmd_changeWavelength.start(change_wavelength_topic,
                                                                             timeout=timeout)
        self.log.info(change_wavelength_ack.ack.ack)

    async def start_propagate_laser(self, timeout=10):
        """startPropagate command

        Parameters
        ----------
        timeout

        Returns
        -------

        """
        start_propagate_laser_topic = self.remote.cmd_startPropagateLaser.DataType()
        start_propagate_laser_ack = await self.remote.cmd_startPropagateLaser.start(
            start_propagate_laser_topic, timeout=timeout)
        self.log.info(start_propagate_laser_ack.ack.ack)

    async def stop_propagate_laser(self, timeout=10):
        """stopPropagate command.

        Parameters
        ----------
        timeout

        Returns
        -------

        """
        stop_propagate_laser_topic = self.remote.cmd_stopPropagateLaser.DataType()
        stop_propagate_laser_ack = await self.remote.cmd_stopPropagateLaser.start(stop_propagate_laser_topic,
                                                                                  timeout=timeout)
        self.log.info(stop_propagate_laser_ack.ack.ack)
