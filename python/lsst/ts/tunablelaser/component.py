"""Implements the component class for the TunableLaser.

"""
import logging
from .ascii import TCPIPClient
from . import hardware


class LaserComponent:
    """The class that implements the TunableLaser component.

    Parameters
    ----------
    simulation_mode : `bool`
        A flag which tells the component to initialize into simulation mode or
        not.

    Attributes
    ----------
    log : `logging.Logger`
        logger for this class.
    commander : `TCPIPClient`
        TCP/IP client.
    cpu8000 : `CPU8000`
        Controls the CPU8000 laser :term:`module`.
    m_cpu800 : `MCPU800`
        Controls the M_CPU800 laser module.
    llpmku : `LLPMKU`
        Controls the llPKMu laser module.
    maxi_opg : `MaxiOPG`
        Controls the MaxiOPG laser module.
    tk6 : `TK6`
        Controls the TK6 laser module.
    hv40w : `HV40W`
        Controls the HV40W laser module.
    delay_lin : `DelayLin`
        Controls the DelayLin laser module.
    mini_opg : `MiniOPG`
        Controls the MiniOPG laser module.
    ldco48bp : `LDCO48BP`
        Controls the LDCO48BP laser module.
    m_ldco48 : `M_LDCO48`
        Controls the LDCO48 laser module.


    """

    def __init__(self, simulation_mode=False, log=None):
        if log is None:
            self.log = logging.getLogger(__name__)
        else:
            self.log = log
        self.commander = None
        self.cpu8000 = hardware.CPU8000(commander=self.commander)
        self.m_cpu800 = hardware.MCPU800(commander=self.commander)
        self.llpmku = hardware.LLPMKU(commander=self.commander)
        self.maxi_opg = hardware.MaxiOPG(commander=self.commander)
        self.tk6 = hardware.TK6(commander=self.commander)
        self.hv40w = hardware.HV40W(commander=self.commander)
        self.delay_lin = hardware.DelayLin(commander=self.commander)
        self.mini_opg = hardware.MiniOPG(commander=self.commander)
        self.ldco48bp = hardware.LDCO48BP(commander=self.commander)
        self.m_ldcO48 = hardware.MLDCO48(commander=self.commander)
        self.is_propgating = False
        self.simulation_mode = simulation_mode
        self.log.info("Laser Component initialized.")

    @property
    def connected(self):
        if self.commander is None:
            return False
        return self.commander.connected

    async def change_wavelength(self, wavelength):
        """Change the wavelength of the laser.

        Parameters
        ----------
        wavelength : `float`
            The wavelength to change to.

            :Units: nanometers
        """
        self.log.debug("Changing wavelength")
        await self.maxi_opg.change_wavelength(wavelength)

    async def set_output_energy_level(self, output_energy_level):
        """Set the output energy level of the laser.

        Parameters
        ----------
        output_energy_level : `str`, {OFF,Adjust,MAX}
            The energy level to set the laser to.

            * OFF: Output energy is off.
            * Adjust: A mode for calibrating the laser.
            * MAX: The maximum energy output of the laser.
        """
        self.log.debug(f"Changing output energy level={output_energy_level}")
        await self.m_cpu800.set_output_energy_level(output_energy_level)

    async def start_propagating(self):
        """Start propagating the beam of the laser."""
        await self.m_cpu800.start_propagating()
        self.is_propgating = True

    async def stop_propagating(self):
        """Stop propagating the beam of the laser"""
        await self.m_cpu800.stop_propagating()
        self.is_propgating = False

    async def clear_fault(self):
        """Clear the fault state of the laser."""
        if self.cpu8000.power_register.register_value == "FAULT":
            await self.cpu8000.power_register.set_register_value("OFF")
        if self.m_cpu800.power_register.register_value == "FAULT":
            await self.m_cpu800.power_register.set_register_value("OFF")
        if self.m_cpu800.power_register_2.register_value == "FAULT":
            await self.m_cpu800.power_register_2.set_register_value("OFF")

    async def read_all_registers(self):
        """Publish the module's registers' values."""
        await self.cpu8000.update_register()
        await self.m_cpu800.update_register()
        await self.llpmku.update_register()
        await self.maxi_opg.update_register()
        await self.mini_opg.update_register()
        await self.tk6.update_register()
        await self.hv40w.update_register()
        await self.delay_lin.update_register()
        await self.ldco48bp.update_register()
        await self.m_ldcO48.update_register()

    async def set_configuration(self, config):
        """Set the configuration for the TunableLaser."""
        self.config = config
        self.log.info("Setting config.")
        self.maxi_opg.wavelength_register.accepted_values = range(
            config.wavelength["min"], config.wavelength["max"]
        )
        self.log.info(
            f"Set min={config.wavelength['min']} & max={config.wavelength['max']} wavelength range."
        )
        self.maxi_opg.optical_alignment = config.optical_configuration
        self.log.info(f"Set optical alignment to {config.optical_configuration}")
        self.log.info(f"Optical alignment is {self.maxi_opg.optical_alignment}")

    async def disconnect(self):
        """Disconnect from the hardware."""
        if self.connected:
            await self.commander.disconnect()

    async def connect(self, host, port):
        """Connect to the hardware.

        Parameters
        ----------
        host : `str`
            The host that the terminal server is hosted on.
        port : `int`
            The port that the terminal server is hosted on.
        """
        if not self.connected:
            self.commander = TCPIPClient(host, port, self.config.timeout)
            self._update_commander()
            await self.set_configuration(self.config)
            await self.commander.connect()
        else:
            raise RuntimeError("Already connected.")

    def _update_commander(self):
        """Update the commander configuration."""
        self.cpu8000 = hardware.CPU8000(commander=self.commander)
        self.m_cpu800 = hardware.MCPU800(commander=self.commander)
        self.llpmku = hardware.LLPMKU(commander=self.commander)
        self.maxi_opg = hardware.MaxiOPG(commander=self.commander)
        self.tk6 = hardware.TK6(commander=self.commander)
        self.hv40w = hardware.HV40W(commander=self.commander)
        self.delay_lin = hardware.DelayLin(commander=self.commander)
        self.mini_opg = hardware.MiniOPG(commander=self.commander)
        self.ldco48bp = hardware.LDCO48BP(commander=self.commander)
        self.m_ldcO48 = hardware.MLDCO48(commander=self.commander)

    def __str__(self):
        return (
            f"{self.cpu8000} {self.m_cpu800} {self.llpmku} {self.maxi_opg} {self.mini_opg} {self.tk6}"
            f"{self.hv40w} {self.delay_lin} {self.ldco48bp} {self.m_ldcO48}"
        )
