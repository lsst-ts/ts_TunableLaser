"""Implements Ascii helper classes for the TunableLaser.

These classes are meant to aid in developing a python wrapper around the ascii
spec used by Ekspla to communicate with the TunableLaser.

Notes
-----
The most important classes are the `TCPIPClient` class and the `AsciiRegister`
class as they contain the bulk of the functionality.

"""
__all__ = ["AsciiRegister", "AsciiError", "TCPIPClient"]
import logging
import enum
import asyncio

from lsst.ts import tcpip


class TCPIPClient:
    """Implements the TCP/IP connection for the TunableLaser

    Parameters
    ----------
    host : `str`
        The host of the TunableLaser server.
    port : `int`
        The port of the TunableLaser server.
    timeout : `float`, optional
        The amount of time that the client waits for reading until timing out
        in seconds.

    Attributes
    ----------
    timeout : `float`
    host : `str`
    port : `int`
    reader : `None` or `StreamReader`
    writer : `None` or `StreamWriter`
    log : `logging.Logger`
    """

    def __init__(self, host, port, timeout=1) -> None:
        self.timeout = timeout
        self.host = host
        self.port = port
        self.reader = None
        self.writer = None
        self.log = logging.getLogger(__name__)
        self.lock = asyncio.Lock()

    @property
    def connected(self) -> bool:
        """Return True if a client is connected to this server.

        Returns
        -------
        bool
        """
        return not (
            self.reader is None
            or self.writer is None
            or self.reader.at_eof()
            or self.writer.is_closing()
        )

    async def connect(self):
        """Connect to the server."""
        if not self.connected:
            async with self.lock:
                connect_task = asyncio.open_connection(self.host, self.port)
                self.reader, self.writer = await asyncio.wait_for(
                    connect_task, self.timeout
                )

    async def disconnect(self):
        """Disconnect from the server.

        Safe to call even if disconnected.
        """
        if self.writer is None:
            return
        try:
            await tcpip.close_stream_writer(self.writer)
        except Exception:
            self.log.exception("disconnect failed, continuing")
        finally:
            self.writer = None
            self.reader = None

    async def send_command(self, message):
        """Send a command to server and receive a reply.

        Parameters
        ----------
        message : `str`
            The command to send to the server.

        Returns
        -------
        reply : `bytes`
            The reply from the server.

        Raises
        ------
        `RuntimeError`
            Raised if the client is not connected.
        """
        if not self.connected:
            raise RuntimeError("Client not connected.")
        async with self.lock:
            self.log.debug(f"message={message.encode('ascii')}")
            message = message.encode("ascii")
            self.writer.write(message)
            await self.writer.drain()
            reply = await self.reader.readuntil(b"\x03")
            reply = self.parse_reply(reply)
            self.log.debug(f"reply={reply.encode('ascii')}")
            return reply

    def parse_reply(self, reply):
        """Return the parsed reply.

        Parameters
        ----------
        reply : `bytes`
            The reply from the server

        Returns
        -------
        decoded_message : `str`
            The decoded and boilerplate stripped string.
        """
        decoded_message = reply.decode("ascii").rstrip("nmC\r\n\x03")
        if decoded_message.startswith("'''"):
            raise Exception(decoded_message)
        return decoded_message


class AsciiRegister:
    """A representation of an Ascii register inside of a module of the laser.

    The class corresponds to a register within a module of a laser. A register
    can be read only or writable.
    If it is read only then the ``accepted_values`` argument is ignored.

    Parameters
    ----------
    commander : `TCPIPClient`
        A TCP/IP stream that writes and reads from the TunableLaser terminal
        server.
    module_name : `str`
        The name of the module that is the parent of the register.
    module_id : `int`
        The id of the module that is the parent of the register.
    register_name : `str`
        The name of the register.
    read_only : `bool`, optional
        Whether the register is read only or writable.
    accepted_values : `list` [`str`] or `list` [`int`] or `None`, optional
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
    commander : `TCPIPClient`
        A TCP/IP client for communicating with the TunableLaser.
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
        commander,
        module_name,
        module_id,
        register_name,
        read_only=True,
        accepted_values=None,
        simulation_mode=False,
    ):
        self.log = logging.getLogger(f"{register_name.replace(' ','')}Register")
        self.commander = commander
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
        self.log.debug(f"get_message={get_message}")
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

    async def read_register_value(self):
        """Read the value of the register.

        Returns
        -------
        None
        """
        message = self.create_get_message()
        self.register_value = await self.commander.send_command(message)
        if self.register_value is None:
            raise TimeoutError

    async def set_register_value(self, set_value):
        """Set the value of the register and read the new value.

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
                self.log.debug(f"sending message {message}.")
                await self.commander.send_command(message)
                await self.read_register_value()
            except TimeoutError:
                self.log.exception("Response timed out.")
                raise
        else:
            self.register_value = set_value

    def __repr__(self):
        return "{}: {}".format(self.register_name, self.register_value)


class AsciiError(enum.Enum):
    pass
