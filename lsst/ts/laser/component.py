"""Implements the component class for the TunableLaser.

"""
import logging
from lsst.ts.laser.hardware import *
from lsst.ts.laser.ascii import *
from lsst.ts.laser.settings import *


class LaserComponent:
    """The class that implements the TunableLaser component.

    Parameters
    ----------
    port: str
        The name of the USB port that the laser connection is located.
    simulation_mode: bool
        A flag which tells the component to initialize into simulation mode or not.

    Attributes
    ----------
    log: logging.Logger
        Creates a logger for this class.
    serial: AsciiSerial
        Creates a serial connection to the laser
    CPU8000: CPU8000
        Controls the CPU8000 :term:`module`.
    M_CPU800: M_CPU800
        Controls the M_CPU800 module.
    llPMKu: llPMKU
        Controls the llPKMu module.
    MaxiOPG: MaxiOPG
        Controls the MaxiOPG module.
    TK6: TK6
        Controls the TK6 module.
    HV40W: HV40W
        Controls the HV40W module.
    DelayLin: DelayLin
        Controls the DelayLin module.
    MiniOPG: MiniOPG
        Controls the MiniOPG module.
    LDCO48BP: LDCO48BP
        Controls the LDCO48BP module.
    M_LDCO48: M_LDCO48
        Controls the LDCO48 module.


    """
    def __init__(self,port: str,configuration,simulation_mode=False):
        self.log = logging.getLogger(__name__)
        self.serial = AsciiSerial(port)
        self.configuration = configuration
        self.CPU8000 = CPU8000(port=self.serial,simulation_mode=simulation_mode)
        self.M_CPU800 = M_CPU800(port=self.serial,simulation_mode=simulation_mode)
        self.llPMKu = llPMKU(port=self.serial,simulation_mode=simulation_mode)
        self.MaxiOPG = MaxiOPG(port=self.serial,simulation_mode=simulation_mode,configuration=self.configuration)
        self.TK6 = TK6(port=self.serial,simulation_mode=simulation_mode)
        self.HV40W = HV40W(port=self.serial,simulation_mode=simulation_mode)
        self.DelayLin = DelayLin(port=self.serial,simulation_mode=simulation_mode)
        self.MiniOPG = MiniOPG(port=self.serial,simulation_mode=simulation_mode)
        self.LDCO48BP = LDCO48BP(port=self.serial,simulation_mode=simulation_mode)
        self.M_LDCO48 = M_LDCO48(port=self.serial,simulation_mode=simulation_mode)
        self.log.info("Laser Component initialized.")

    def change_wavelength(self, wavelength):
        """Changes the wavelength of the laser.

        Parameters
        ----------
        wavelength
            The wavelength to change to.

        Returns
        -------
        None
        """
        self.MaxiOPG.change_wavelength(wavelength)

    def set_output_energy_level(self, output_energy_level):
        """Sets the output energy level of the laser.

        Parameters
        ----------
        output_energy_level: {OFF,Adjust,MAX}
            The energy level to set the laser to.

        Returns
        -------
        None
        """
        self.M_CPU800.set_output_energy_level(output_energy_level)

    def start_propagating(self):
        """Starts propagating the beam of the laser.

        Returns
        -------
        None

        """
        self.M_CPU800.start_propagating()

    def stop_propagating(self):
        """Stops propagating the beam of the laser

        Returns
        -------
        None
        """
        self.M_CPU800.stop_propagating()

    def clear_fault(self):
        """Clears the fault state of the laser.

        Returns
        -------

        """
        if self.CPU8000.power_register.register_value == "FAULT":
            self.CPU8000.power_register.set_register_value("OFF")
        if self.M_CPU800.power_register.register_value == "FAULT":
            self.M_CPU800.power_register.set_register_value("OFF")
        if self.M_CPU800.power_register_2.register_value == "FAULT":
            self.M_CPU800.power_register_2.set_register_value("OFF")

    def publish(self):
        """Publishes the module's registers' values.

        Returns
        -------
        None
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

    def __str__(self):
        return "{} {} {} {} {} {} {} {} {} {}".format(
            self.CPU8000,
            self.M_CPU800,
            self.llPMKu,
            self.MaxiOPG,
            self.MiniOPG,
            self.TK6,
            self.HV40W,
            self.DelayLin,
            self.LDCO48BP,
            self.M_LDCO48
        )


def main():
    logging.basicConfig(level=logging.DEBUG)
    lc = LaserComponent("/dev/ttyACM0",configuration=laser_configuration())
    lc.publish()
    print(lc)
    lc.change_wavelength(626)
    lc.publish()
    print(lc)
    lc.MaxiOPG.set_configuration("No SCU")
    lc.publish()
    print(lc)
    lc.MaxiOPG.set_configuration("Bob")
    lc.publish()
    print(lc)


if __name__ == '__main__':
    main()
