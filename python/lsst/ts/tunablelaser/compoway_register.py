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

import io

from .register import AsciiRegister


class CompoWayFGeneralRegister(AsciiRegister):
    def __init__(
        self,
        component,
        module_name,
        module_id,
        register_name,
        read_only=True,
        accepted_values=None,
    ) -> None:
        super().__init__(
            component=component,
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
            b"0000": "Normal completion",
            b"0401": "Unsupported command",
            b"1001": "Command too long",
            b"1002": "Command too short",
            b"1101": "Area type error",
            b"1103": "Start address out-of-range error",
            b"1104": "End address out-of-range error",
            b"1003": "Number of elements/data mismatch",
            b"110B": "Response too long",
            b"1100": "Parameter error",
            b"3003": "Read-only error",
            b"2203": "Operation error",
        }

        self.end_code_dict = {
            b"00": "Normal completion",
            b"0F": "FINS command error",
            b"10": "Parity error",
            b"11": "Framing error",
            b"12": "Overrun error",
            b"13": "BCC error",
            b"14": "Format error",
            b"16": "Sub-address error",
            b"18": "Frame length error",
        }

        # for parsing responses
        self.end_code = "00"
        self.response_code = ""
        self.cmd_txt = ""
        self.BCC = ""

    def generate_bcc(self, frame):
        result = 0
        for char in frame:
            char_in_int = int(hex(ord(char)), 0)
            result = result ^ char_in_int
        return chr(result)

    def compoway_cmd_frame(self, pdu_structure):
        cmd_frame = self.node + "00" + "0" + pdu_structure + "\x03"
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
        cmd_txt = (
            MRC + SRC + variable_code + read_address + bit_position + read_elements
        )
        get_message = self.compoway_cmd_frame(cmd_txt)
        self.log.debug(f"get_message={get_message}")
        return get_message

    def _create_set_message_generic(
        self, variable_code, write_address, write_elements, data
    ):
        MRC = "\x30\x31"
        SRC = "\x30\x32"
        bit_position = "\x30\x30"
        cmd_txt = (
            MRC
            + SRC
            + variable_code
            + write_address
            + bit_position
            + write_elements
            + data
        )
        return self.compoway_cmd_frame(cmd_txt)

    def _create_operation_message_generic(self, command_code, related_info):
        MRC = "\x33\x30"
        SRC = "\x30\x35"
        cmd_txt = MRC + SRC + command_code + related_info
        return self.compoway_cmd_frame(cmd_txt)

    def create_get_message(self):
        # need to override the ascii register
        raise Exception(
            "Function not implemented, you shouldn't be using the generic class"
        )

    def create_set_message(self, set_value):
        # need to override the ascii register
        raise Exception(
            "Function not implemented, you shouldn't be using the generic class"
        )

    async def read_register_value(self):
        # need to override the ascii register
        raise Exception(
            "Function not implemented, you shouldn't be using the generic class"
        )

    async def set_register_value(self, set_value):
        # need to override the ascii register
        raise Exception(
            "Function not implemented, you shouldn't be using the generic class"
        )

    def get_response(self):
        if self.response_code in self.response_dict:
            return self.response_dict[self.response_code]
        else:
            return "Invalid response code"

    def get_end_code(self):
        if self.end_code in self.end_code_dict:
            return self.end_code_dict[self.end_code]
        else:
            return "Invalid end code"

    def get_data(self):
        return self.cmd_txt


class CompoWayFDataRegister(CompoWayFGeneralRegister):
    def __init__(
        self,
        component,
        module_name,
        module_id,
        register_name,
        read_only=True,
        accepted_values=None,
        simulation_mode=False,
    ) -> None:
        super().__init__(
            component=component,
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

        self.register_address_dict = {
            "Set Point": "\x30\x30\x30\x33",
        }

        if (
            register_name not in self.variable_code_dict
            or register_name not in self.register_address_dict
        ):
            raise ValueError("Unsupported module name")

        if read_only is False and accepted_values is None:
            raise ValueError(
                "Can't have read only register without giving accepted values"
            )

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
            if set_value not in self.accepted_values:
                raise ValueError(f"{set_value} not in {self.accepted_values}")

            # This read_elements setting only reads 1 word of data (4 digits)
            # If this needs to change/be configurable in the future one way
            # is to make a dictionary like its done for reg address/variable
            write_elements = "\x30\x30\x30\x31"

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

    async def read_register_value(self):
        """Read the value of the register.

        Returns
        -------
        None
        """
        message = self.create_get_message()
        response = await self.component.commander.write(message)

        with io.BytesIO(response) as f:
            try:
                stx_node_subadd = f.read(5)
                expected_stx_node_subadd = "\x02" + self.node + "\x30\x30"
                if stx_node_subadd is not expected_stx_node_subadd:
                    raise Exception(
                        f"Received incorrect start of packet: {stx_node_subadd}, "
                        f"expected: {expected_stx_node_subadd}"
                    )
                self.end_code = f.read(2)
                mrc_src = f.read(4)
                # read variable area request MRC is 01, SRC is 01
                expected_mrc_src = "\x01\x01"
                if mrc_src is not expected_mrc_src:
                    raise Exception(
                        f"Received incorrect Request Codes: {mrc_src}, "
                        f"expected: {expected_mrc_src}"
                    )
                self.response_code = f.read(4)

                # bytesio doesn't include a readuntil
                # the cmdtxt can be variable length, demarked by ETX byte
                # This read_elements setting only reads 1 word (4 bytes)
                # If this needs to be configurable in the future one way
                # is to make a dictionary like its done for register add
                # Doing range 8 for comfort, should only be 4 + 1 for ETX
                # TODO calculate maximum message length dynamically and
                # TODO add for when f runs out of bytes
                self.cmd_txt = b""
                for _ in range(8):
                    byte = f.read(1)
                    # ETX byte
                    if byte == b"\x03":
                        break
                    else:
                        self.cmd_txt = self.cmd_txt + byte

                self.BCC = f.read(1)

                # TODO check message's BCC to make sure its good
            except Exception:
                raise Exception(f"Message format not as expected. Message: {response}")

        self.register_value = self.cmd_txt

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
                await self.component.commander.write(message)
                await self.read_register_value()
            except TimeoutError:
                self.log.exception("Response timed out.")
                raise
        else:
            self.register_value = set_value


class CompoWayFOperationRegister(CompoWayFGeneralRegister):
    def __init__(
        self,
        component,
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
            component=component,
            module_name=module_name,
            module_id=module_id,
            register_name=register_name,
            read_only=read_only,
            accepted_values=accepted_values,
        )

        self.command_code_dict = {
            "Run Stop": "\x38\x31",
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

        set_message = self._create_operation_message_generic(
            command_code=self.command_code, related_info=str(set_value)
        )

        self.log.debug(f"set_message={set_message}")
        return set_message

    async def read_register_value(self):
        # can't read operational registers
        raise Exception("Can't read operational registers")

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
                await self.component.commander.write(message)
            except TimeoutError:
                self.log.exception("Response timed out.")
                raise
        else:
            self.register_value = set_value
