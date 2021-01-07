import logging
import queue
import serial
import inspect


class MockSerial(serial.Serial):
    def __init__(
        self,
        port,
        baudrate=19200,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=3,
        xonxoff=False,
        rtscts=False,
        write_timeout=None,
        dsrdtr=False,
        inter_byte_timeout=None,
        exclusive=None,
    ):
        super().__init__(port=port)
        self.log = logging.getLogger(__name__)

        self.device = MockNT900()
        self.message_queue = queue.Queue()

        self.log.info("MockSerial created")

    def read_until(self, character):
        self.log.info("Reading from queue")
        msg = self.message_queue.get()
        self.log.info(msg.encode("ascii"))
        return msg.encode("ascii")

    def write(self, data):
        self.log.info(data)
        msg = self.device.parse_message(data)
        self.log.debug(msg)
        self.message_queue.put(msg)
        self.log.info("Putting into queue")


class MockMessage:
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
    def __init__(self):
        self.wavelength = 650
        self.temperature = 19
        self.current = "19A"
        self.propagating = "OFF"
        self.output_energy_level = "OFF"
        self.configuration = "No SCU"
        self.log = logging.getLogger(__name__)

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
        return f"{self.wavelength}nm\r\n\x03"

    def do_change_wavelength(self, wavelength):
        self.wavelength = wavelength
        return "\r\n\x03"

    def do_change_power(self, state):
        self.propagating = state
        return "\r\n\x03"

    def do_power(self):
        return f"{self.propagating}\r\n\x03"

    def do_display_current(self):
        return f"{self.current}\r\n\x03"

    def do_fault_code(self):
        return "0\r\n\x03"

    def do_continuous_burst_mode_trigger_burst(self):
        return "Continuous\r\n\x03"

    def do_output_energy_level(self):
        return f"{self.output_energy_level}\r\n\x03"

    def do_change_output_energy_level(self, energy_level):
        self.output_energy_level = energy_level
        return "\r\n\x03"

    def do_frequency_divider(self):
        return "0\r\n\x03"

    def do_burst_pulses_to_go(self):
        return "0\r\n\x03"

    def do_qsw_adjustment_output_delay(self):
        return "0\r\n\x03"

    def do_repetition_rate(self):
        return "1\r\n\x03"

    def do_synchronization_mode(self):
        return "0\r\n\x03"

    def do_burst_length(self):
        return "1\r\n\x03"

    def do_configuration(self):
        return f"{self.configuration}\r\n\x03"

    def do_change_configuration(self, configuration):
        self.configuration = configuration
        return "\r\n\x03"

    def do_error_code(self):
        return "0\r\n\x03"

    def do_display_temperature(self):
        return f"{self.temperature}C\r\n\x03"

    def do_set_temperature(self):
        return f"{self.temperature}C\r\n\x03"

    def do_hv_voltage(self):
        return "10\r\n\x03"
