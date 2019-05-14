"""Implements the component class for the TunableLaser.

"""
import logging
from .hardware import CPU8000, M_CPU800, llPMKU, MaxiOPG, MiniOPG, TK6, HV40W, DelayLin, \
    LDCO48BP, M_LDCO48
from .ascii import AsciiSerial


class LaserComponent:
    """The class that implements the TunableLaser component.

    Parameters
    ----------
    port: str
        The name of the USB port that the laser connection is located.
    configuration: dict
        A dict that is created from :func:`laser_configuration`
    simulation_mode: bool
        A flag which tells the component to initialize into simulation mode or not.

    Attributes
    ----------
    log : `logging.Logger`
        Creates a logger for this class.
    serial: `AsciiSerial`
        Creates a serial connection to the laser
    CPU8000: `CPU8000`
        Controls the CPU8000 :term:`module`.
    M_CPU800: `M_CPU800`
        Controls the M_CPU800 module.
    llPMKu: `llPMKU`
        Controls the llPKMu module.
    MaxiOPG: `MaxiOPG`
        Controls the MaxiOPG module.
    TK6: `TK6`
        Controls the TK6 module.
    HV40W: `HV40W`
        Controls the HV40W module.
    DelayLin: `DelayLin`
        Controls the DelayLin module.
    MiniOPG: `MiniOPG`
        Controls the MiniOPG module.
    LDCO48BP: `LDCO48BP`
        Controls the LDCO48BP module.
    M_LDCO48: `M_LDCO48`
        Controls the LDCO48 module.


    """
    def __init__(self, simulation_mode=False):
        self.log = logging.getLogger(__name__)
        self.serial = AsciiSerial(None)
        self.CPU8000 = CPU8000(port=self.serial, simulation_mode=simulation_mode)
        self.M_CPU800 = M_CPU800(port=self.serial, simulation_mode=simulation_mode)
        self.llPMKu = llPMKU(port=self.serial, simulation_mode=simulation_mode)
        self.MaxiOPG = MaxiOPG(port=self.serial, simulation_mode=simulation_mode)
        self.TK6 = TK6(port=self.serial, simulation_mode=simulation_mode)
        self.HV40W = HV40W(port=self.serial, simulation_mode=simulation_mode)
        self.DelayLin = DelayLin(port=self.serial, simulation_mode=simulation_mode)
        self.MiniOPG = MiniOPG(port=self.serial, simulation_mode=simulation_mode)
        self.LDCO48BP = LDCO48BP(port=self.serial, simulation_mode=simulation_mode)
        self.M_LDCO48 = M_LDCO48(port=self.serial, simulation_mode=simulation_mode)
        self.configuration = None
        self.log.info("Laser Component initialized.")

    def change_wavelength(self, wavelength):
        """Changes the wavelength of the laser.

        Parameters
        ----------
        wavelength: float
            The wavelength to change to.
            
            * Units: nanometers

        Returns
        -------
        None
        """
        self.MaxiOPG.change_wavelength(wavelength)

    def set_output_energy_level(self, output_energy_level):
        """Sets the output energy level of the laser.

        Parameters
        ----------
        output_energy_level: str, {OFF,Adjust,MAX}
            The energy level to set the laser to.
            
            * OFF: Output energy is off.
            * Adjust: A mode for calibrating the laser.
            * MAX: The maximum energy output of the laser.

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

        Notes
        -----
        This method is designed for integrating with the CSC class and so serves as a auxiliary to 
        "publish" to the CSC :meth:`publish` the updated values of the component. Hence why it is called 
        publish.

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

    def set_simulation_mode(self,mode):
        self.simulation_mode = mode
        self.CPU8000.set_simulation_mode(mode)
        self.M_CPU800.set_simulation_mode(mode)
        self.llPMKu.set_simulation_mode(mode)
        self.MaxiOPG.set_simulation_mode(mode)
        self.MiniOPG.set_simulation_mode(mode)
        self.TK6.set_simulation_mode(mode)
        self.HV40W.set_simulation_mode(mode)
        self.DelayLin.set_simulation_mode(mode)
        self.LDCO48BP.set_simulation_mode(mode)
        self.M_LDCO48.set_simulation_mode(mode)

    def set_configuration(self):
        if not self.simulation_mode:
            self.serial.port=self.configuration.port
        self.MaxiOPG.wavelength_register.accepted_values=range(self.configuration.wavelength['min'],self.configuration.wavelength['max'])
        self.MaxiOPG.optical_alignment = self.configuration.optical_configuration

    def disconnect(self):
        if not self.simulation_mode:
            self.serial.close()

    def connect(self):
        if not self.simulation_mode:
            self.serial.open()

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
    lc = LaserComponent("/dev/ttyACM0", configuration=laser_configuration())
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
