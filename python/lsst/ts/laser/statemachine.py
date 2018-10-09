from lsst.ts.statemachine.states import EnabledState, DefaultState, DisabledState, StandbyState, FaultState, OfflineState
from lsst.ts.statemachine.context import Context
from lsst.ts.laser.component import LaserComponent
from typing import Dict
import logging
from salpytools import salpylib

logger = logging.getLogger(__name__)


class LaserEnabledState(EnabledState):
    def __init__(self):
        super(LaserEnabledState, self).__init__('Laser')

    def change_wavelength(self, model):
        model.change_wavelength(self.data.wavelength)
        return 0, 'done'

    def start_propagating(self, model):
        model.change_state("PROPAGATING")
        return 0, 'done'


class LaserPropagatingState(DefaultState):
    def __init__(self):
        super(LaserPropagatingState, self).__init__('PROPAGATING', 'Laser')

    def stop_propagating(self, model):
        model.change_state("ENABLED")
        return 0, 'done'

    def change_wavelength(self, model):
        model.change_wavelength(self.data.wavelength)
        return 0, 'done'


class LaserModel:
    def __init__(self, port: str):
        self.state: str = "OFFLINE"
        self.previous_state: str = None
        self._laser: LaserComponent = LaserComponent(port)
        self._port: str = port
        self.temperature: float = None
        self.wavelength: float = None
        self._dds: salpylib.DDSSend = salpylib.DDSSend('Laser')
        self._ss_dictionary: Dict[str, int] = {"OFFLINE": 5, "STANDBY": 4, "DISABLED": 1, "ENABLED": 2, "FAULT": 3}
        self._ds_dictionary: Dict[str, int] = {"OFFLINE": 5, "STANDBY": 4, "DISABLED": 1, "ENABLED": 2, "FAULT": 3}
        self.frequency: float = 0.05

    def change_state(self, state: str) -> None:
        logger.debug(self.state)
        self.previous_state = self.state
        self.state = state
        self._dds.send_Event('summaryState', SummaryState=self._ss_dictionary[state])
        self._dds.send_Event('detailedState', DetailedState=self._ds_dictionary[state])
        logger.debug(self.state)

    def change_wavelength(self, wavelength: int) -> None:
        self._laser.MaxiOPG.set_wavelength(wavelength)
        self._dds.send_Telemetry('wavelength', wavelength=wavelength)
        self.wavelength = self._laser.MaxiOPG.wavelength


class LaserCSC:
    def __init__(self, port: str):
        self.model = LaserModel(port)
        self.subsystem_tag = 'Laser'
        self.states = {"OFFLINE":OfflineState('Laser'),"DISABLED":DisabledState('Laser'),"ENABLED":LaserEnabledState(),"STANDBY":StandbyState,"FAULT": FaultState('Laser'),"PROPAGATING": LaserPropagatingState}
        self.context = Context(self.subsystem_tag, self.model, states=self.states)
        self.context.add_command('changeWavelength','change_wavelength')
        self.entercontrol = salpylib.DDSController(context=self.context, command='enterControl')
        self.start = salpylib.DDSController(context=self.context, command='start')
        self.enable = salpylib.DDSController(context=self.context, command='enable')
        self.disable = salpylib.DDSController(context=self.context, command='disable')
        self.exitcontrol = salpylib.DDSController(context=self.context, command='exitControl')
        self.standby = salpylib.DDSController(context=self.context, command='standby')
        self.start_propagating = salpylib.DDSController(context=self.context, command='start_propagating')
        self.stop_propagating = salpylib.DDSController(context=self.context, command='stop_propagating')
        self.change_wavelength = salpylib.DDSController(context=self.context, command='change_wavelength')


    def run(self):
        self.entercontrol.start()
        self.start.start()
        self.enable.start()
        self.disable.start()
        self.exitcontrol.start()
        self.standby.start()
        self.start_propagating.start()
        self.stop_propagating.start()
        self.change_wavelength.start()

    def stop_csc(self, signum, frame):
        logger.info('Received signal %s [%s]... Stopping components...', signum, frame)
        self.entercontrol.stop()
        self.start.stop()
        self.enable.stop()
        self.disable.stop()
        self.exitcontrol.stop()
        self.standby.stop()
        self.start_propagating.stop()
        self.stop_propagating.stop()
        self.change_wavelength.stop()
        logger.info('Waiting for threads to finish...')
        self.entercontrol.join()
        self.start.join()
        self.enable.join()
        self.disable.join()
        self.exitcontrol.join()
        self.start_propagating.join()
        self.stop_propagating.join()
        self.change_wavelength.join()
        logger.info('Done')
