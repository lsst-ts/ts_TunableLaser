"""Implements Ascii helper classes for the TunableLaser.

These classes are meant to aid in developing a python wrapper around the ascii
spec used by Ekspla to communicate with the TunableLaser.

Notes
-----
The most important classes are the `AsciiSerial` class and the `AsciiRegister`
class as they contain the bulk of the functionality.

"""
__all__ = ["SerialCommander", "AsciiRegister", "AsciiError"]
import logging
import serial
import enum


class SerialCommander:
    """A class which inherits serial.Serial in order to provide helper
    functions for communicating with the laser.

    This class extends the class `serial.Serial` in order to provide
    helper methods in order to parse the expected reply and then return the
    reply for handling by `AsciiRegister`.

    Parameters
    ----------
    port : `str`
    timeout : `int`
        The amount of time to wait before reporting the port as timed out.

    Attributes
    ----------
    log : `logging.Logger`

    """

    def __init__(self, port, timeout=5, num_of_tries=3):
        self.log = logging.getLogger(__name__)
        self.num_of_tries = num_of_tries
        self.commander = serial.Serial(port=port, baudrate=19200, timeout=timeout)

    def send_command(self, message):
        """Write the message to the serial port, parses the reply and then
        returns it for processing by `AsciiRegister`.

        Parameters
        ----------
        message : `bytes`

        Returns
        -------
        reply : `str`
            The parsed reply returned by :meth:`parse_reply`.

        """
        message = message.encode("ascii")
        for num_of_tries in range(self.num_of_tries):
            try:
                self.commander.write(message)
                reply = self.parse_reply(self.commander.read_until(b"\x03"))
            except TimeoutError:
                reply = None
                self.commander.flush()
                self.log.exception("Port Timed out")
            except Exception as e:
                self.log.exception(e)
                raise
            else:
                return reply

    def parse_reply(self, message):
        """Parse the reply as expected by Ascii spec provided by the vendor.

        Parameters
        ----------
        message : `bytes`

        Raises
        ------
        AsciiError


        Returns
        -------
        stripped_message : `str`

        """
        decoded_message = message.decode("ascii")
        self.log.debug(f"decoded message is {decoded_message}")
        stripped_message = decoded_message.rstrip("nmC\r\n\x03")
        self.log.debug(f"stripped message is {stripped_message}")
        if stripped_message.startswith("'''"):
            self.log.error(f"Port returned {stripped_message}")
            raise Exception(stripped_message)
        return stripped_message


class AsciiRegister:
    """A representation of an Ascii register inside of a module of the laser.

    The class corresponds to a register within a module of a laser. A register
    can be read only or writable.
    If it is read only then the ``accepted_values`` argument is ignored.
    The simulation_mode has not been implemented at this time.

    Parameters
    ----------
    port : `AsciiSerial`
        A serial port that writes and reads from the TunableLaser converter
        module.
    module_name : `str`
        The name of the module that is the parent of the register.
    module_id : `int`
        The id of the module that is the parent of the register.
    register_name : `str`
        The name of the register.
    read_only : `bool`, optional
        Whether the register is read only or writable.
    accepted_values : `list` [`str`] or `list` [`int`] or `None`
        If read_only is set to true then this parameter can be None. If not,
        this parameter must contain a list of values accepted by this
        register and can be of int or str.
    simulation_mode : `bool`, optional
        A bool representing whether the register is in simulation mode or not.
        Currently is not implemented.

    Attributes
    ----------
    log : `logging.Logger`
        The log for this class.
    port : `SerialCommander`
        A serial port for communicating with the TunableLaser.
    module_name : `str`
        The name of the module that is the parent of the register.
    module_id : `int`
        The id of the module that is the parent of the register.
    register_name : `str`
        The name of the register.
    read_only : `bool`
        Whether the register is read only or writable.
    accepted_values : `list`
        If read_only is set to true then this parameter can be None.
        If not, this parameter must contain a list of values accepted by this
        register and can be of int or str.
    simulation_mode : `bool`
        A bool representing whether the register is in simulation mode or not.
        Currently has a basic implementation.
    register_value : `str`
        The value of the register as gotten by :meth:`get_register_value`.

    """

    def __init__(
        self,
        port,
        module_name,
        module_id,
        register_name,
        read_only=True,
        accepted_values=None,
        simulation_mode=False,
    ):
        self.log = logging.getLogger(f"{register_name.replace(' ','')}Register")
        self.port = port
        self.module_name = module_name
        self.module_id = module_id
        self.register_name = register_name
        self.read_only = read_only
        if not self.read_only and accepted_values is None:
            raise AttributeError(
                "If read_only is false than accepted_values should not be None."
            )
        self.accepted_values = accepted_values
        self.simulation_mode = simulation_mode
        self.register_value = None
        self.log.debug(f"{self.register_name} Register initialized")

    def create_get_message(self):
        """Generate the message that will get the register value.

        Returns
        -------
        get_message: `bytes`

        """
        get_message = f"/{self.module_name}/{self.module_id}/{self.register_name}\r"
        self.log.debug(f"{get_message}")
        return get_message

    def create_set_message(self, set_value):
        """Create the message that sets the value of the register provided
        that it is not read only.

        Parameters
        ----------
        set_value : Any

        Raises
        ------
        ReadOnlyException
            Indicates that the register is read only.
        ValueError
            Indicates that the value received is not in the acceptable values
            for the register.

        Returns
        -------
        set_message : `bytes`

        """
        if not self.read_only:
            if set_value not in self.accepted_values:
                raise ValueError(f"{set_value} not in {self.accepted_values}")
            set_message = (
                f"/{self.module_name}/{self.module_id}/{self.register_name}/"
                f"{set_value}\r"
            )
            self.log.debug(f"set_message={set_message}")
            return set_message
        else:
            raise PermissionError("This register is read only.")

    def get_register_value(self):
        """Get the value of the register.

        """
        message = self.create_get_message()
        self.register_value = self.port.send_command(message)
        if self.register_value is None:
            raise TimeoutError

    def set_register_value(self, set_value):
        """Set the value of the register.

        Parameters
        ----------
        set_value : Any

        Raises
        ------
        ReadOnlyException
            This indicates that the register is read only and cannot be set.

        Returns
        -------
        None

        """
        if self.read_only:
            raise PermissionError("This register is read only.")
        if not self.simulation_mode:
            try:
                message = self.create_set_message(set_value)
                self.log.debug("sending message to serial port.")
                self.port.send_command(message)
            except TimeoutError:
                self.log.exception("Response timed out.")
                raise
        else:
            self.register_value = set_value

    def __repr__(self):
        return "{}: {}".format(self.register_name, self.register_value)


class AsciiError(enum.Enum):
    pass
