import logging
from lsst.ts.laser.component import LaserComponent
import salobj
import SALPY_TunableLaser
import asyncio
import enum


class LaserDetailedStateEnum(enum.Enum):
    DISABLEDSTATE = 1
    ENABLEDSTATE = 2
    FAULTSTATE = 3
    OFFLINESTATE = 4
    STANDBYSTATE = 5
    PROPAGATINGSTATE = 6


class LaserCSC(salobj.BaseCsc):
    def __init__(self,address,frequency=1, initial_state=salobj.State.STANDBY):
        super().__init__(SALPY_TunableLaser)
        self.model = LaserModel(address)
        self.frequency = frequency
        self.wavelength_topic = self.tel_wavelength.DataType()
        self.temperature_topic = self.tel_temperature.DataType()
        self.summary_state = initial_state
        asyncio.ensure_future(self.telemetry())

    async def telemetry(self):
        while True:
            self.model.publish()
            if self.model.fault_code == "0002H":
                self.fault()
            self.wavelength_topic.wavelength = float(self.model._laser.MaxiOPG.wavelength[:-2])
            self.temperature_topic.temperature = float(self.model._laser.TK6.temperature[:-1])
            self.tel_wavelength.put(self.wavelength_topic)
            self.tel_temperature.put(self.temperature_topic)
            await asyncio.sleep(self.frequency)

    def assert_propagating(self, action):
        if self.detailed_state != LaserDetailedStateEnum.PROPAGATINGSTATE:
            raise salobj.ExpectedError(f"{action} not allowed in state {self.detailed_state}")

    async def do_changeWavelength(self,id_data):
        self.assert_enabled("changeWavelength")
        self.model.change_wavelength(id_data.data.wavelength)

    async def do_startPropagateLaser(self,id_data):
        self.assert_enabled("startPropagateLaser")
        self.model.run()
        self.detailed_state = LaserDetailedStateEnum.PROPAGATINGSTATE

    async def do_stopPropagateLaser(self,id_data):
        self.assert_enabled("stopPropagateLaser")
        self.assert_propagating("stopPropagateLaser")
        self.model.stop()
        self.detailed_state = LaserDetailedStateEnum.ENABLEDSTATE

    async def do_abort(self,id_data):
        pass

    async def do_clearFaultState(self, id_data):
        self.model.stop()

    async def do_setValue(self, id_data):
        pass

    async def do_enterControl(self, id_data):
        pass

    @property
    def detailed_state(self):
        detailed_state_topic = self.evt_detailedState.DataType()
        return detailed_state_topic.detailedState

    @detailed_state.setter
    def detailed_state(self,new_sub_state):
        detailed_state_topic = self.evt_detailedState.DataType()
        detailed_state_topic.detailedState = new_sub_state
        self.evt_detailedState.put(detailed_state_topic)

    def end_enable(self, id_data):
        self._end_enable()

    async def _end_enable(self):
        self.model._laser.MaxiOPG.set_configuration("No SCU")
        self.model._laser.M_CPU800.set_energy("MAX")


class LaserModel:
    def __init__(self,port):
        self._laser = LaserComponent(port)
        self.propagate_status = self._laser.M_CPU800.propagate_state
        self.fault_code = self._laser.M_CPU800.fault
        self.wavelength = float(self._laser.MaxiOPG.wavelength[:-2])
        self.temperature = float(self._laser.TK6.temperature[:-1])

    def change_wavelength(self,wavelength):
        self._laser.MaxiOPG.set_wavelength(wavelength)

    def run(self):
        self._laser.M_CPU800.set_propagate("ON")

    def stop(self):
        self._laser.M_CPU800.set_propagate("OFF")

    def publish(self):
        self._laser._publish()


class LaserDeveloperRemote:
    def __init__(self):
        self.remote = salobj.Remote(SALPY_TunableLaser)
        self.log = logging.getLogger(__name__)

    async def standby(self,timeout=10):
        standby_topic = self.remote.cmd_standby.DataType()
        standby_ack = await self.remote.cmd_standby.start(standby_topic,timeout=timeout)
        self.log.info(standby_ack.ack.ack)

    async def start(self,timeout=10):
        start_topic = self.remote.cmd_start.DataType()
        start_ack = await self.remote.cmd_start.start(start_topic,timeout=timeout)
        self.log.info(start_ack.ack.ack)

    async def enable(self,timeout=10):
        enable_topic = self.remote.cmd_enable.DataType()
        enable_ack = await self.remote.cmd_enable.start(enable_topic,timeout=timeout)
        self.log.info(enable_ack.ack.ack)

    async def disable(self,timeout=10):
        disable_topic = self.remote.cmd_disable.DataType()
        disable_ack = await self.remote.cmd_disable.start(disable_topic,timeout=timeout)
        self.log.info(disable_ack.ack.ack)

    async def change_wavelength(self, wavelength,timeout=10):
        change_wavelength_topic = self.remote.cmd_changeWavelength.DataType()
        change_wavelength_topic.wavelength = float(wavelength)
        change_wavelength_ack = await self.remote.cmd_changeWavelength.start(change_wavelength_topic,timeout=timeout)
        self.log.info(change_wavelength_ack.ack.ack)

    async def start_propagate_laser(self,timeout=10):
        start_propagate_laser_topic = self.remote.cmd_startPropagateLaser.DataType()
        start_propagate_laser_ack = await self.remote.cmd_startPropagateLaser.start(start_propagate_laser_topic,timeout=timeout)
        self.log.info(start_propagate_laser_ack.ack.ack)

    async def stop_propagate_laser(self,timeout=10):
        stop_propagate_laser_topic = self.remote.cmd_stopPropagateLaser.DataType()
        stop_propagate_laser_ack = await self.remote.cmd_stopPropagateLaser.start(stop_propagate_laser_topic,timeout=timeout)
        self.log.info(stop_propagate_laser_ack.ack.ack)