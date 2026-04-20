# This file is part of ts_tunablelaser.
#
# Developed for the Vera Rubin Observatory Telescope and Site Software.
# This product includes software developed by the LSST Project
# (https://www.lsst.org).
# See the COPYRIGHT file at the top-level directory of this distribution
# for details of code ownership.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


__all__ = [
    "CompoWayFGeneralRegister",
    "CompoWayFDataRegister",
    "CompoWayFOperationRegister",
]

from .register import AsciiRegister


class CompoWayFGeneralRegister(AsciiRegister):
    """A general representation of a register using the CompoWayF standard.

    This class only defines parts of the packet formation that are shared by
    the various types of register types (operation, data, etc...)

    Parameters
    ----------
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

    Attributes
    ----------
    log : `logging.Logger`
        The log for this class.
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
    register_value : `str`
        The value of the register as gotten by :meth:`get_register_value`.

    """

    def __init__(
        self,
        module_name="",
        module_id=0,
        register_name="",
        read_only=True,
        accepted_values=None,
    ) -> None:
        super().__init__(
            module_name=module_name,
            module_id=module_id,
            register_name=register_name,
            read_only=read_only,
            accepted_values=accepted_values,
        )

        self.node = str(module_id)

        self.set_value = None
        self.status = None

        self.response_dict = {
            "0000": "Normal completion",
            "0401": "Unsupported command",
            "1001": "Command too long",
            "1002": "Command too short",
            "1101": "Area type error",
            "1103": "Start address out-of-range error",
            "1104": "End address out-of-range error",
            "1003": "Number of elements/data mismatch",
            "110B": "Response too long",
            "1100": "Parameter error",
            "3003": "Read-only error",
            "2203": "Operation error",
        }

        self.end_code_dict = {
            "00": "Normal completion",
            "0F": "FINS command error",
            "10": "Parity error",
            "11": "Framing error",
            "12": "Overrun error",
            "13": "BCC error",
            "14": "Format error",
            "16": "Sub-address error",
            "18": "Frame length error",
        }

        # for parsing responses
        self.end_code = "00"
        self.response_code = ""
        self.cmd_txt = ""
        self.bcc = ""

    # Frame should be whole packet, without STX byte but WITH ETX byte
    def generate_bcc(self, frame):
        """Generate bcc.

        Parameters
        ----------
        frame : `bytes`
            The frame.
        """
        if isinstance(frame, bytes):
            self.log.error(f"bytes sent into generate_bcc, decoding... {frame}")
            frame = frame.decode()
        result = 0
        for char in frame:
            char = str(char)
            char_in_int = int(ord(char))
            result = result ^ char_in_int
        return chr(result)

    def compoway_cmd_frame(self, pdu_structure):
        """Compoway cmd frame.

        Parameters
        ----------
        pdu_structure
            The structure of the pdu.
        """
        if len(self.node) == 1:
            node = "0" + self.node
        elif len(self.node) == 2:
            node = self.node
        else:
            raise ValueError(
                f"Incorrect length of node, expected length 2, got {len(self.node)} {self.node}."
            )
        cmd_frame = node + "00" + "0" + pdu_structure + "\x03"
        cmd_frame = cmd_frame.upper()
        cmd_frame = cmd_frame + self.generate_bcc(cmd_frame)
        cmd_frame = "\x02" + cmd_frame
        return cmd_frame

    def _create_get_message_generic(self, variable_code, read_address, read_elements):
        """Generate the message that will get the register value.

        Returns
        -------
        get_message: `bytes`

        """
        MRC = "\x30\x31"
        SRC = "\x30\x31"
        bit_position = "\x30\x30"
        cmd_txt = MRC + SRC + variable_code + read_address + bit_position + read_elements
        get_message = self.compoway_cmd_frame(cmd_txt).upper()
        self.log.debug(f"get_message={get_message}")
        return get_message

    def _create_set_message_generic(self, variable_code, write_address, write_elements, data):
        """Create a set message."""
        MRC = "\x30\x31"
        SRC = "\x30\x32"
        bit_position = "\x30\x30"
        cmd_txt = MRC + SRC + variable_code + write_address + bit_position + write_elements + data
        return self.compoway_cmd_frame(cmd_txt)

    def _create_operation_message_generic(self, command_code, related_info):
        """Create operation message."""
        MRC = "\x33\x30"
        SRC = "\x30\x35"
        cmd_txt = MRC + SRC + command_code + related_info
        return self.compoway_cmd_frame(cmd_txt)

    def create_get_message(self):
        """Create get message."""
        # need to override the ascii register
        raise Exception("Function not implemented, you shouldn't be using the generic class")

    def create_set_message(self, set_value):
        """Create set message."""
        # need to override the ascii register
        raise Exception("Function not implemented, you shouldn't be using the generic class")

    def get_response(self):
        """Get response."""
        translated_response = self.response_code
        if isinstance(self.response_code, bytes):
            translated_response = translated_response.decode()
        if translated_response in self.response_dict:
            return self.response_dict[translated_response]
        else:
            return "Invalid response code"

    def get_end_code(self):
        """Get end code."""
        translated_end_code = self.end_code
        if isinstance(self.end_code, bytes):
            translated_end_code = translated_end_code.decode()
        if translated_end_code in self.end_code_dict:
            return self.end_code_dict[translated_end_code]
        else:
            return "Invalid end code"

    def get_data(self):
        """Get data."""
        return self.cmd_txt


class CompoWayFDataRegister(CompoWayFGeneralRegister):
    """Specific data register implementation using the CompoWayF standard.

    Parameters
    ----------
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
    simulation_mode : `bool`
        A bool representing whether the register is in simulation mode or not.

    Attributes
    ----------
    log : `logging.Logger`
        The log for this class.
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
        Only needed to append '\r' to string for the tcpip.client
    register_value : `str`
        The value of the register as gotten by :meth:`get_register_value`.

    Raises
    --------
    ValueError
        If the register_name is an unsupported command
        If the register is selected to be writeable,
                but no accepted_values is given.

    """

    def __init__(
        self,
        module_name,
        module_id,
        register_name,
        read_only=True,
        accepted_values=None,
        simulation_mode=False,
    ) -> None:
        if read_only is False and isinstance(accepted_values, range) is False:
            raise TypeError("accepted_values must be type range")

        super().__init__(
            module_name=module_name,
            module_id=module_id,
            register_name=register_name,
            read_only=read_only,
            accepted_values=accepted_values,
        )

        self.simulation_mode = simulation_mode

        # Note this is hardcoding to read words of data instead of double words
        # If this changes to accommodate double words then multiple places in
        # the class need updating these places are denoted by comments as well
        self.variable_code_dict = {
            "Set Point": "\x38\x31",
        }

        # Dictionary of implemented commands
        self.register_address_dict = {
            "Set Point": "\x30\x30\x30\x33",
        }

        if register_name not in self.variable_code_dict or register_name not in self.register_address_dict:
            raise ValueError("Unsupported module name")

        if read_only is False and accepted_values is None:
            raise ValueError("Can't have writeable register without giving accepted values")

        self.variable_code = self.variable_code_dict[register_name]
        self.register_address = self.register_address_dict[register_name]

    def create_get_message(self):
        """Generate the message that will get the register value.

        Returns
        -------
        get_message: `bytes`

        """
        # This read_elements setting only reads 1 word of data (4 digits)
        # If this needs to change/be configurable in the future one way
        # is to make a dictionary like its done for register address/variable
        read_elements = "\x30\x30\x30\x31"

        get_message = self._create_get_message_generic(
            variable_code=self.variable_code,
            read_address=self.register_address,
            read_elements=read_elements,
        )

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
            if set_value < min(self.accepted_values) or set_value > max(self.accepted_values):
                raise ValueError(f"{set_value} not in {self.accepted_values}")

            set_value = int(set_value * 10)

            # This read_elements setting only reads 1 word of data (4 digits)
            # If this needs to change/be configurable in the future one way
            # is to make a dictionary like its done for reg address/variable
            write_elements = "\x30\x30\x30\x31"
            if (set_value * -1) > 0x7FFF:
                raise ValueError(f"AbsVal of set value too large (>0x7FFF) {set_value}")

            # do 2's complement
            if set_value < 1:
                set_value = hex(((set_value * -1) ^ 0xFFFF) + 1)
            else:
                set_value = hex(set_value)

            set_value = set_value.split("x")[1]

            if len(set_value) > 4:
                self.log.exception(f"set value too long (4 length max): {set_value}")
                raise ValueError
            while len(set_value) < 4:
                set_value = "0" + set_value

            set_message = self._create_set_message_generic(
                variable_code=self.variable_code,
                write_address=self.register_address,
                write_elements=write_elements,
                data=str(set_value),
            )

            self.log.debug(f"set_message={set_message}")
            return set_message
        else:
            raise PermissionError("This register is read only.")


class CompoWayFOperationRegister(CompoWayFGeneralRegister):
    """Specific operation register implementation using the CompoWayF standard.

    Parameters
    ----------
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
    simulation_mode : `bool`
        A bool representing whether the register is in simulation mode or not.

    Attributes
    ----------
    log : `logging.Logger`
        The log for this class.
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
        Only needed to append '\r' to string for the tcpip.client
    register_value : `str`
        The value of the register as gotten by :meth:`get_register_value`.

    Raises
    ----------
    ValueError
        If the register_name is not a supported command

    """

    def __init__(
        self,
        module_name,
        module_id,
        register_name,
        accepted_values,
        simulation_mode=False,
    ) -> None:
        self.simulation_mode = simulation_mode

        # operation registers are write-only
        read_only = False

        super().__init__(
            module_name=module_name,
            module_id=module_id,
            register_name=register_name,
            read_only=read_only,
            accepted_values=accepted_values,
        )

        # dictionary of implemented commands
        self.command_code_dict = {
            "Run Stop": "\x30\x31",
        }

        self.run_stop_related_info = {
            True: "\x30\x30",  # on
            False: "\x30\x31",  # off
        }

        if register_name not in self.command_code_dict:
            raise ValueError("Unsupported module name")

        self.command_code = self.command_code_dict[register_name]

    def create_get_message(self):
        """Generate the message that will get the register value.

        Returns
        -------
        get_message: `bytes`

        """
        # Operation registers dont have ability to get
        raise Exception("Operation registers cannot 'get'")

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
        if set_value not in self.accepted_values:
            raise ValueError(f"{set_value} not in {self.accepted_values}")

        set_value = self.get_related_info(set_value)
        if set_value is None:
            self.log.exception(f"set value not found {set_value}")
            raise ValueError

        set_message = self._create_operation_message_generic(
            command_code=self.command_code, related_info=str(set_value)
        )

        self.log.debug(f"set_message={set_message}")
        return set_message

    def get_related_info(self, set_value):
        """Get related info."""
        chosen_dict = None
        # RUN/STOP
        if self.command_code == "\x30\x31":
            chosen_dict = self.run_stop_related_info
        else:
            self.log.error(f"No valid command code in get_related_info: {self.command_code}")
        if set_value in chosen_dict:
            return chosen_dict[set_value]
        else:
            self.log.error(f"No set value ({set_value}) in chosen dict ({chosen_dict})")
            return None
