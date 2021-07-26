__all__ = ["MockServer", "MockMessage", "MockNT900"]

import logging
import inspect
import asyncio

from lsst.ts import tcpip


class MockServer(tcpip.OneClientServer):
    """Simulates the TunableLaser.

    Parameters
    ----------
    port : `int`, optional
        The port that the server will start on.
    """

    def __init__(self, port=0) -> None:
        self.device = MockNT900()
        self.log = logging.getLogger(__name__)
        self.read_loop_task = asyncio.Future()
        super().__init__(
            name="TunableLaser Mock Server",
            host=tcpip.LOCAL_HOST,
            port=port,
            log=self.log,
            connect_callback=self.connect_callback,
        )

    def connect_callback(self, server):
        """Call when the client connects.

        Starts the command loop for the simulator.

        Parameters
        ----------
        server : `lsst.ts.tcpip.OneClientServer`
        """
        self.read_loop_task.cancel()
        if server.connected:
            self.read_loop_task = asyncio.create_task(self.cmd_loop())

    async def cmd_loop(self):
        """Return reply based on messaged received."""
        while self.connected:
            self.log.debug("inside cmd_loop")
            reply = await self.reader.readuntil(b"\r")
            if not reply:
                self.writer.close()
                return
            reply = self.device.parse_message(reply)
            self.log.debug(f"reply={reply.encode('ascii')}")
            self.writer.write(reply.encode("ascii"))
            await self.writer.drain()


class MockMessage:
    """Parse a command from the client.

    Parameters
    ----------
    msg : `bytes`
        The bytes received from the client.

    Raises
    ------
    `Exception`
        Raised when a message is malformed.
    """

    def __init__(self, msg):
        msg = msg.decode("ascii").strip("\r\n\x03")
        split_msg = msg.split("/")
        if len(split_msg) == 4:
            self.register_name = split_msg[1]
            self.register_id = split_msg[2]
            self.register_field = split_msg[3].lower()
            split_register_field = self.register_field.split(" ")
            self.register_field = "_".join(split_register_field)
        elif len(split_msg) == 5:
            self.register_name = split_msg[1]
            self.register_id = split_msg[2]
            self.register_field = split_msg[3].lower()
            split_register_field = self.register_field.split(" ")
            self.register_field = "_".join(split_register_field)
            self.register_parameter = split_msg[4]
        elif split_msg[0].startswith("```"):
            self.exception = split_msg
        else:
            raise Exception("Message malformed")

    def __repr__(self):
        return f"{self.register_name}\n{self.register_id}\n{self.register_field}\n"


class MockNT900:
    """Implements a mock NT900 laser.

    Attributes
    ----------
    wavelength : `float`
        The wavelength of the laser.
    temperature : `float`
        The temperature of the laser.
    current : `str`
        The electrical current of the laser.
    propagating : `str`
        Whether the laser is propagating.
    output_energy_level : `str`
        The energy level of the laser's output
    configuration : `str`
        Which output the laser is propagating from.
    log : `logging.Logger`
        The log for this class.
    """

    def __init__(self):
        self.wavelength = 650
        self.temperature = 19
        self.current = "19A"
        self.propagating = "OFF"
        self.output_energy_level = "OFF"
        self.configuration = "No SCU"
        self.log = logging.getLogger(__name__)
        self.log.debug("MockNT900 initialized")

    def parse_message(self, msg):
        """Parse and return the result of the message.

        Parameters
        ----------
        msg : `bytes`
            The message to parse.

        Returns
        -------
        reply : `bytes`
            The reply of the command parsed.

        Raises
        ------
        NotImplementedError
            Raised when command is not implemented.
        """
        try:
            self.log.info(msg)
            split_msg = MockMessage(msg)
            self.log.debug(split_msg)
            command_name = split_msg.register_field
            self.log.debug(f"{command_name}")
            if not hasattr(split_msg, "register_parameter"):
                parameter = None
            else:
                parameter = split_msg.register_parameter
                command_name = "change_" + command_name
            self.log.debug(f"{parameter}")
            command_name = "do_" + command_name
            self.log.debug(command_name)
            if hasattr(split_msg, "exception"):
                reply = split_msg.exception
                return reply
            methods = inspect.getmembers(self, inspect.ismethod)
            for name, func in methods:
                if name == command_name:
                    self.log.debug(command_name)
                    if parameter is None:
                        reply = func()
                    else:
                        reply = func(parameter)
                    self.log.debug(f"reply: {reply}")
                    return reply
                elif command_name == "do_continuous_%2f_burst_mode_%2f_trigger_burst":
                    self.log.debug(command_name)
                    reply = self.do_continuous_burst_mode_trigger_burst()
                    self.log.debug(f"reply: {reply}")
                    return reply
            raise NotImplementedError()
        except Exception as e:
            self.log.exception(e)
            raise Exception

    def do_wavelength(self):
        """Return current wavelength as formatted string.

        Returns
        -------
        `str`
        """
        return f"{self.wavelength}nm\r\n\x03"

    def do_change_wavelength(self, wavelength):
        """Change wavelength as formatted string.

        Returns
        -------
        `str`
        """
        self.wavelength = wavelength
        return "\r\n\x03"

    def do_change_power(self, state):
        """Change power output as formatted string.

        Returns
        -------
        `str`
        """
        self.propagating = state
        return "\r\n\x03"

    def do_power(self):
        """Return current power output as formatted string.

        Returns
        -------
        `str`
        """
        return f"{self.propagating}\r\n\x03"

    def do_display_current(self):
        """Return current as formatted string.

        Returns
        -------
        `str`
        """
        return f"{self.current}\r\n\x03"

    def do_fault_code(self):
        """Return current fault code as formatted string.

        Returns
        -------
        `str`
        """
        return "0\r\n\x03"

    def do_continuous_burst_mode_trigger_burst(self):
        """Return current laser propagation mode as formatted string.

        Returns
        -------
        `str`
        """
        return "Continuous\r\n\x03"

    def do_output_energy_level(self):
        """Return current output energy level as formatted string.

        Returns
        -------
        `str`
        """
        return f"{self.output_energy_level}\r\n\x03"

    def do_change_output_energy_level(self, energy_level):
        """Change output energy level as formatted string.

        Returns
        -------
        `str`
        """
        self.output_energy_level = energy_level
        return "\r\n\x03"

    def do_frequency_divider(self):
        """Return current frequency divider as formatted string.

        Returns
        -------
        `str`
        """
        return "0\r\n\x03"

    def do_burst_pulses_to_go(self):
        """Return current burst pulses left as formatted string.

        Returns
        -------
        `str`
        """
        return "0\r\n\x03"

    def do_qsw_adjustment_output_delay(self):
        """Return current qsw adjustment output delay as formatted string.

        Returns
        -------
        `str`
        """
        return "0\r\n\x03"

    def do_repetition_rate(self):
        """Return current repetition rate as formatted string.

        Returns
        -------
        `str`
        """
        return "1\r\n\x03"

    def do_synchronization_mode(self):
        """Return current synchronization mode as formatted string.

        Returns
        -------
        `str`
        """
        return "0\r\n\x03"

    def do_burst_length(self):
        """Return current burst length as formatted string.

        Returns
        -------
        `str`
        """
        return "1\r\n\x03"

    def do_configuration(self):
        """Return current configuration as formatted string.

        Returns
        -------
        `str`
        """
        return f"{self.configuration}\r\n\x03"

    def do_change_configuration(self, configuration):
        """Change the configuration as formatted string.

        Returns
        -------
        `str`
        """
        self.configuration = configuration
        return "\r\n\x03"

    def do_error_code(self):
        """Return current error code as formatted string.

        Returns
        -------
        `str`
        """
        return "0\r\n\x03"

    def do_display_temperature(self):
        """Return current temperature as formatted string.

        Returns
        ------
        `str`
        """
        return f"{self.temperature}C\r\n\x03"

    def do_set_temperature(self):
        """Change setpoint temperature as formatted string.

        Returns
        -------
        `str`
        """
        return f"{self.temperature}C\r\n\x03"

    def do_hv_voltage(self):
        """Return current hv voltage as formatted string.

        Returns
        -------
        `str`
        """
        return "10\r\n\x03"
