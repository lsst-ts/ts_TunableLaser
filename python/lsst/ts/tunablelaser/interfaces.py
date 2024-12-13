__all__ = ["Laser", "CompoWayFModule"]

from abc import ABC, abstractmethod

from lsst.ts import tcpip
from lsst.ts.tunablelaser.wizardry import NUMBER_OF_RETRIES


class Laser(ABC):
    """Implement common Laser interface.

    Parameters
    ----------
    csc : `LaserCSC`
        The CSC object.
    terminator : `bytes`
        The characters that terminate sent/received messages.
    encoding : `str`
        The type of encoding to use.
    simulation_mode : `bool`, optional
        Is the laser being simulated?

    Attributes
    ----------
    csc : `LaserCSC`
        The CSC object.
    terminator : `bytes`
        The characters that terminate sent/received messages.
    encoding : `str`
        The type of encoding to use.
    log : `logging.Logger`
        The log of the component.
    simulation_mode : `bool`
        Is the laser being simulated?
    commander : `lsst.ts.tcpip.Client`
        A TCP/IP client.
    """

    def __init__(self, csc, terminator, encoding, simulation_mode=False) -> None:
        self.csc = csc
        self.terminator = terminator
        self.encoding = encoding
        self.log = csc.log
        self.simulation_mode = simulation_mode
        self.commander = tcpip.Client(host="", port=0, log=self.log)

    @property
    @abstractmethod
    def is_propagating(self):
        """Is the laser propagating?"""
        raise NotImplementedError

    @property
    def connected(self):
        """Is the laser connected?"""
        return self.commander.connected

    @property
    def should_be_connected(self):
        return self.commander.should_be_connected

    @property
    @abstractmethod
    def wavelength(self):
        """The wavelength of the laser."""
        raise NotImplementedError

    @property
    @abstractmethod
    def temperature(self):
        """The temperature sensors."""
        raise NotImplementedError

    @abstractmethod
    def change_wavelength(self, wavelength):
        """Change the wavelength.

        Parameters
        ----------
        wavelength: `float`
            The value to change the wavelength.
        """
        raise NotImplementedError

    @abstractmethod
    def set_output_energy_level(self, output_energy_level):
        """Set the output energy level.

        Parameters
        ----------
        output_energy_level:
            The laser's energy level.
        """
        raise NotImplementedError

    @abstractmethod
    def trigger_burst(self):
        """Trigger burst."""
        raise NotImplementedError

    @abstractmethod
    def set_burst_mode(self, count):
        """Set the burst mode and count."""
        raise NotImplementedError

    @abstractmethod
    def start_propagating(self):
        """Start propagating the laser."""
        raise NotImplementedError

    @abstractmethod
    def stop_propagating(self):
        """Stop propagating the laser."""
        raise NotImplementedError

    @abstractmethod
    def clear_fault(self):
        """Clear the fault state of the laser."""
        raise NotImplementedError

    @abstractmethod
    def configure(self, config):
        """Configure the laser."""
        raise NotImplementedError

    async def disconnect(self):
        """Disconnect from the laser."""
        await self.commander.close()
        self.commander = tcpip.Client(host="", port=0, log=self.log)

    async def connect(self):
        """Connect to the laser."""
        if self.csc.simulation_mode:
            self.host = self.csc.simulator.host
            self.port = self.csc.simulator.port
        for _ in range(NUMBER_OF_RETRIES):
            try:
                self.commander = tcpip.Client(
                    host=self.host,
                    port=self.port,
                    log=self.log,
                    terminator=bytes(self.terminator),
                    encoding=self.encoding,
                )
                await self.commander.start_task
            except Exception:
                self.log.exception("Connection failed.")
            if self.commander.connected:
                break


class CanbusModule(ABC):
    """Implement canbus module for the laser.

    Parameters
    ----------
    component : `Laser`
        A reference to the laser component.

    Attributes
    ----------
    component : `Laser`
        A reference to the laser component.
    """

    def __init__(self, component) -> None:
        self.component = component
        super().__init__()

    async def update_register(self):
        """Update the registers located in the canbus module."""
        pass


class CompoWayFModule(ABC):
    """Implement CompoWayF Module.

    Parameters
    ----------
    csc : `LaserCSC`
        The CSC object.
    terminator : `bytes`
        The characters that terminate sent/received messages.
    encoding : `str`
        The type of encoding to use.
    simulation_mode : `bool`, optional
        Is the laser being simulated?

    Attributes
    ----------
    csc : `LaserCSC`
        The CSC object.
    terminator : `bytes`
        The characters that terminate sent/received messages.
    encoding : `str`
        The type of encoding to use.
    log : `logging.Logger`
        The log of the component.
    simulation_mode : `bool`
        Is the module being simulated?
    commander : `lsst.ts.tcpip.Client`
        A TCP/IP client.
    """

    def __init__(
        self, csc, terminator=b"\x03", encoding="utf-8", simulation_mode=False
    ) -> None:
        self.csc = csc
        self.encoding = encoding
        self.log = csc.log
        self.simulation_mode = simulation_mode
        self.terminator = terminator
        self.commander = tcpip.Client(host="", port=0, log=self.log)

    @property
    def connected(self):
        """Is the module connected?"""
        return self.commander.connected

    @property
    @abstractmethod
    def temperature(self):
        """The temperature sensors."""
        raise NotImplementedError

    @abstractmethod
    def configure(self, config):
        """Configure the module."""
        raise NotImplementedError

    async def disconnect(self):
        """Disconnect from the module."""
        await self.commander.close()
        self.commander = tcpip.Client(host="", port=0, log=self.log)

    async def connect(self):
        """Connect to the module."""
        if self.host is not None:
            self.commander = tcpip.Client(
                host=self.host,
                port=self.port,
                log=self.log,
                terminator=bytes(self.terminator),
                encoding=self.encoding,
            )
            await self.commander.start_task
