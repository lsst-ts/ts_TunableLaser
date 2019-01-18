"""Implements Ascii helper classes for the TunableLaser.

These classes are meant to aid in developing a python wrapper around the ascii spec used by Ekspla to
communicate with the TunableLaser.

Notes
-----
The most important classes are the :class:`AsciiSerial` class and the :class:`AsciiRegister` class as they
contain the bulk of the functionality.

"""
__all__ = ["AsciiSerial", "AsciiRegister", "AsciiError", "ReadOnlyException"]
import logging
import serial


class AsciiSerial(serial.Serial):
    """A class which inherits serial.Serial in order to provide helper functions for communication handling
    with the laser.

    This class extends the class :class:`serial.Serial` in order to provide helper methods in order to parse
    the expected reply and then return the reply for handling by :class:`AsciiRegister`.

    Parameters
    ----------
    port: str
    timeout: 5
        The amount of time to wait before reporting the port as timed out.

    Attributes
    ----------
    log: logging.Logger

    """
    def __init__(self, port,timeout=5):
        super(AsciiSerial, self).__init__(port, baudrate=19200, timeout=timeout)
        self.log = logging.getLogger(__name__)

    def perform_magic(self, message):
        """Writes the message to the serial port, parses the reply and then returns it for processing by
        :class:`AsciiRegister`.

        Parameters
        ----------
        message: bytearray

        Returns
        -------
        reply: str
            The parsed reply returned by :meth:`parse_reply`.

        """
        self.write(message)
        reply = self.parse_reply(self.read_until(b"\x03"))
        return reply

    def parse_reply(self, message):
        """Parses the reply as expected by Ascii spec provided by the vendor.

        Parameters
        ----------
        message: bytearray

        Raises
        ------
        AsciiError


        Returns
        -------
        stripped_message: str

        """
        decoded_message = message.decode()
        self.log.debug(f"decoded message is {decoded_message}")
        stripped_message = decoded_message.strip('\r\n\x03')
        self.log.debug(f"stripped message is {stripped_message}")
        if stripped_message.startswith("'''"):
            self.log.error(f"Port returned {stripped_message}")
            raise AsciiError(stripped_message)
        return stripped_message


class AsciiRegister:
    """A representation of an Ascii register inside of a module of the laser.

    The class corresponds to a register within a module of a laser. A register can be read only or writable.
    If it is read only, then the accepted_values do not matter in this case, but if it is writable then the
    accepted_values do matter. The simulation_mode has not been implemented at this time.

    .. warning::
        The simulation_mode parameter has not been handled at this time. Setting it will not change any
        functionality of this component.

    Parameters
    ----------
    port: AsciiSerial
        A serial port that writes and reads from the TunableLaser converter module.
    module_name: str
        The name of the module that is the parent of the register.
    module_id: int
        The id of the module that is the parent of the register.
    register_name: str
        The name of the register.
    read_only: bool, optional
        Whether the register is read only or writable.
    accepted_values: Optional[List[int,str]], optional
        If read_only is set to true then this parameter can be None. If not, this parameter must contain a
        list of values accepted by this register and can be of int or str.
    simulation_mode: bool, optional
        A bool representing whether the register is in simulation mode or not. Currently is not implemented.

    Attributes
    ----------
    log: logging.Logger
        The log for this class.
    port: AsciiSerial
        A serial port for communicating with the TunableLaser.
    module_name: str
        The name of the module that is the parent of the register.
    module_id: int
        The id of the module that is the parent of the register.
    register_name: str
        The name of the register.
    read_only: bool
        Whether the register is read only or writable.
    accepted_values: Optional[List[Any]]
        If read_only is set to true then this parameter can be None. If not, this parameter must contain a
        list of values accepted by this register and can be of int or str.
    simulation_mode: bool
        A bool representing whether the register is in simulation mode or not. Currently is not implemented.
    register_value: str
        The value of the register as gotten by :meth:`get_register_value`.

    """
    def __init__(
            self, port, module_name, module_id, register_name, read_only=True, accepted_values=None,
            simulation_mode=False):
        self.log = logging.getLogger(f"{register_name.replace(' ','')}Register")
        self.port = port
        self.module_name = module_name
        self.module_id = module_id
        self.register_name = register_name
        self.read_only = read_only
        self.accepted_values = accepted_values
        self.simulation_mode = simulation_mode
        self.register_value = None
        self.log.debug(f"{self.register_name} Register initialized")

    def create_get_message(self):
        """Generates the message that will get the register value.

        Returns
        -------
        get_message: bytearray

        """
        get_message = "/{0}/{1}/{2}\r".format(self.module_name, self.module_id, self.register_name).encode(
            'ascii')
        self.log.debug(f"{get_message}")
        return get_message

    def create_set_message(self, set_value):
        """Creates the message that sets the value of the register provided that it is not read only.

        Parameters
        ----------
        set_value: Any

        Raises
        ------
        ReadOnlyException
            Indicates that the register is read only.
        ValueError
            Indicates that the value received is not in the acceptable values for the register.

        Returns
        -------
        set_message: bytearray

        """
        if not self.read_only:
            if set_value in self.accepted_values:
                set_message = "/{0}/{1}/{2}/{3}\r".format(
                    self.module_name, self.module_id, self.register_name, set_value).encode('ascii')
                self.log.debug(f"{set_message}")
                return set_message
            elif self.accepted_values is None:
                raise AttributeError("self.accepted_values must be defined.")
            else:
                raise ValueError("{1} not in {0}".format(self.accepted_values, set_value))
        else:
            raise ReadOnlyException("This register is read only.")

    def get_register_value(self):
        """Gets the value of the register.

        Returns
        -------
        None

        """
        message = self.create_get_message()
        self.register_value = self.port.perform_magic(message)

    def set_register_value(self, set_value):
        """Sets the value of the register provided the register is not read only.

        Parameters
        ----------
        set_value: Any

        Raises
        ------
        ReadOnlyException
            This indicates that the register is read only and cannot be set.

        Returns
        -------
        None

        """
        if not self.read_only:
            message = self.create_set_message(set_value)
            self.log.debug("sending message to serial port.")
            self.port.perform_magic(message)
        else:
            raise ReadOnlyException("This register is read only.")

    def __str__(self):
        return "{}: {}".format(self.register_name, self.register_value)


class ReadOnlyException(Exception):
    """This exception is for a register that is considered read-only.

    """
    pass


class AsciiError(Exception):
    """Corresponds to an error with the Ascii spec produced by the laser.

    """
    pass
