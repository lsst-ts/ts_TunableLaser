"""Implements the component class for the TunableLaser.

"""
import logging
import pty
import os
from . import hardware
from .ascii import SerialCommander
from .mock_server import MockSerial


class LaserComponent:
    """The class that implements the TunableLaser component.

    Parameters
    ----------
    port: `str`
        The name of the USB port that the laser connection is located.
    configuration: `dict`
        A dict that is created from :func:`laser_configuration`
    simulation_mode: `bool`
        A flag which tells the component to initialize into simulation mode or
        not.

    Attributes
    ----------
    log : `logging.Logger`
        logger for this class.
    serial : `AsciiSerial`
        serial connection to the laser
    CPU8000 : `CPU8000`
        Controls the CPU8000 laser :term:`module`.
    M_CPU800 : `M_CPU800`
        Controls the M_CPU800 laser module.
    llPMKu : `llPMKU`
        Controls the llPKMu laser module.
    MaxiOPG : `MaxiOPG`
        Controls the MaxiOPG laser module.
    TK6 : `TK6`
        Controls the TK6 laser module.
    HV40W : `HV40W`
        Controls the HV40W laser module.
    DelayLin : `DelayLin`
        Controls the DelayLin laser module.
    MiniOPG : `MiniOPG`
        Controls the MiniOPG laser module.
    LDCO48BP : `LDCO48BP`
        Controls the LDCO48BP laser module.
    M_LDCO48 : `M_LDCO48`
        Controls the LDCO48 laser module.


    """

    def __init__(self, simulation_mode=False):
        self.log = logging.getLogger(__name__)
        self.serial = SerialCommander(None)
        self.CPU8000 = hardware.CPU8000(port=self.serial)
        self.M_CPU800 = hardware.MCPU800(port=self.serial)
        self.llPMKu = hardware.LLPMKU(port=self.serial)
        self.MaxiOPG = hardware.MaxiOPG(port=self.serial)
        self.TK6 = hardware.TK6(port=self.serial)
        self.HV40W = hardware.HV40W(port=self.serial)
        self.DelayLin = hardware.DelayLin(port=self.serial)
        self.MiniOPG = hardware.MiniOPG(port=self.serial)
        self.LDCO48BP = hardware.LDCO48BP(port=self.serial)
        self.M_LDCO48 = hardware.MLDCO48(port=self.serial)
        self.connected = False
        self.is_propgating = False
        self.simulation_mode = simulation_mode
        self.log.info("Laser Component initialized.")

    def change_wavelength(self, wavelength):
        """Change the wavelength of the laser.

        Parameters
        ----------
        wavelength : `float`
            The wavelength to change to.

            :Units: nanometers
        """
        self.log.debug("Changing wavelength")
        self.MaxiOPG.change_wavelength(wavelength)

    def set_output_energy_level(self, output_energy_level):
        """Set the output energy level of the laser.

        Parameters
        ----------
        output_energy_level : `str`, {OFF,Adjust,MAX}
            The energy level to set the laser to.

            * OFF: Output energy is off.
            * Adjust: A mode for calibrating the laser.
            * MAX: The maximum energy output of the laser.
        """
        self.log.debug("Changing output energy level")
        self.M_CPU800.set_output_energy_level(output_energy_level)

    def start_propagating(self):
        """Start propagating the beam of the laser.
        """
        self.M_CPU800.start_propagating()
        self.is_propgating = True

    def stop_propagating(self):
        """Stop propagating the beam of the laser
        """
        self.M_CPU800.stop_propagating()
        self.is_propgating = False

    def clear_fault(self):
        """Clear the fault state of the laser.
        """
        if self.CPU8000.power_register.register_value == "FAULT":
            self.CPU8000.power_register.set_register_value("OFF")
        if self.M_CPU800.power_register.register_value == "FAULT":
            self.M_CPU800.power_register.set_register_value("OFF")
        if self.M_CPU800.power_register_2.register_value == "FAULT":
            self.M_CPU800.power_register_2.set_register_value("OFF")

    def publish(self):
        """Publish the module's registers' values.

        Notes
        -----
        This method is designed for integrating with the CSC class and so
        serves as a auxiliary to "publish" to the CSC :meth:`publish` the
        updated values of the component. Hence why it is called publish.
        """
        self.CPU8000.publish()
        self.M_CPU800.publish()
        self.llPMKu.publish()
        self.MaxiOPG.publish()
        self.MiniOPG.publish()
        self.TK6.publish()
        self.HV40W.publish()
        self.DelayLin.publish()
        self.LDCO48BP.publish()
        self.M_LDCO48.publish()

    def set_configuration(self, config):
        if not self.simulation_mode:
            self.serial.port = config.port
        self.MaxiOPG.wavelength_register.accepted_values = range(
            config.wavelength["min"], config.wavelength["max"]
        )
        self.MaxiOPG.optical_alignment = config.optical_configuration

    def disconnect(self):
        if self.serial.commander is not None:
            self.serial.commander.close()
            self.connected = False

    def connect(self):
        if not self.simulation_mode:
            self.serial.commander.commander.open()
            self.connected = True
        else:
            main, reader = pty.openpty()
            self.serial.commander = MockSerial(os.ttyname(main))
            self._update_serial()
            # self.serial.commander.open()
            self.connected = True

    def _update_serial(self):
        self.CPU8000.port = self.serial
        self.M_CPU800.port = self.serial
        self.M_LDCO48.port = self.serial
        self.MaxiOPG.port = self.serial
        self.MiniOPG.port = self.serial
        self.DelayLin.port = self.serial
        self.LDCO48BP.port = self.serial
        self.TK6.port = self.serial
        self.HV40W.port = self.serial
        self.llPMKu.port = self.serial

    def __str__(self):
        return (
            f"{self.CPU8000} {self.M_CPU800} {self.llPMKu} {self.MaxiOPG} {self.MiniOPG} {self.TK6}"
            f"{self.HV40W} {self.DelayLin} {self.LDCO48BP} {self.M_LDCO48}"
        )
