from lsst.ts.laser.component import LaserComponent
import salobj
import SALPY_TunableLaser
import asyncio

class LaserCSC(salobj.BaseCsc):
    def __init__(self,address,frequency=2,initial_state=salobj.State.STANDBY):
        super().__init__(SALPY_TunableLaser)
        self.model = LaserModel(address)
        self.frequency = frequency
        self.wavelength_topic = self.tel_wavelength.DataType()
        self.temperature_topic = self.tel_temperature.DataType()
        self.summary_state = initial_state

    async def telemetry(self):
        while True:
            self.wavelength_topic.wavelength = self.model.wavelength
            self.temperature_topic = self.model.temperature
            self.tel_wavelength.put(self.wavelength_topic)
            self.tel_temperature.put(self.temperature_topic)
            asyncio.sleep(self.frequency)

    async def do_changeWavelength(self,id_data):
        self.assert_enabled("changeWavelength")
        self.model.change_wavelength(id_data.data.wavelength)

    async def do_startPropagateLaser(self,id_data):
        self.assert_enabled("startPropagateLaser")
        self.model.run()
        self.detailed_state = self.salinfo.lib.detailedState_DetailedState_PropagatingState

    async def do_stopPropagateLaser(self,id_data):
        self.assert_enabled("stopPropagateLaser")
        self.model.stop()
        self.detailed_state = self.salinfo.lib.detailedState_DetailedState_EnabledState

    @property
    def detailed_state(self):
        detailed_state_topic = self.evt_detailedState.DataType()
        return detailed_state_topic.detailedState

    @detailed_state.setter
    def detailed_state(self,new_sub_state):
        detailed_state_topic = self.evt_detailedState.DataType()
        detailed_state_topic.detailedState = new_sub_state
        self.evt_detailedState.put(detailed_state_topic)


class LaserModel:
    def __init__(self,port):
        self._laser = LaserComponent(port)
        self.wavelength = self._laser.MaxiOPG.wavelength
        self.temperature = self._laser.TK6.temperature

    def change_wavelength(self,wavelength):
        self._laser.MaxiOPG.change_wavelength(wavelength)

    def run(self):
        self._laser.M_CPU800.set_propagate("ON")

    def stop(self):
        self._laser.M_CPU800.set_propagate("OFF")