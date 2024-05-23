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
    component : `Laser`
        Reference to the component.
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
    register_value : `str`
        The value of the register as gotten by :meth:`get_register_value`.

    """

    def __init__(
        self,
        component=None,
        module_name="",
        module_id=0,
        register_name="",
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
        if isinstance(frame, bytes):
            self.log.error(f"bytes sent into generate_bcc, decoding... {frame}")
            frame = frame.decode().strip()
        result = 0
        for char in frame:
            char = str(char)
            char_in_int = int(ord(char))
            result = result ^ char_in_int
        return chr(result)

    def compoway_cmd_frame(self, pdu_structure):
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
        cmd_txt = (
            MRC + SRC + variable_code + read_address + bit_position + read_elements
        )
        get_message = self.compoway_cmd_frame(cmd_txt).upper()
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

    def compare_string_values(self, expected, received):
        passed = True
        for expected, got in zip(expected, received):
            if ord(expected) is not ord(got):
                passed = False
        return passed

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
        translated_response = self.response_code
        if isinstance(self.response_code, bytes):
            translated_response = translated_response.decode().strip()
        if translated_response in self.response_dict:
            return self.response_dict[translated_response]
        else:
            return "Invalid response code"

    def get_end_code(self):
        translated_end_code = self.end_code
        if isinstance(self.end_code, bytes):
            translated_end_code = translated_end_code.decode().strip()
        if translated_end_code in self.end_code_dict:
            return self.end_code_dict[translated_end_code]
        else:
            return "Invalid end code"

    def get_data(self):
        return self.cmd_txt


class CompoWayFDataRegister(CompoWayFGeneralRegister):
    """Specific data register implementation using the CompoWayF standard.

    Parameters
    ----------
    component : `Laser`
        Reference to the component.
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
        component,
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

        # Dictionary of implemented commands
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
                "Can't have writeable register without giving accepted values"
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
            if set_value < min(self.accepted_values) or set_value > max(
                self.accepted_values
            ):
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

    async def read_register_value(self):
        """Read the value of the register.

        Returns
        -------
        None
        """
        async with self.component.lock:
            message = self.create_get_message()

            if self.simulation_mode:
                message += "\r"

            await self.component.commander.write(
                message.encode(self.component.commander.encoding)
            )

            try:
                error_triggered = False
                packet = await self.component.commander.readuntil(b"\x03")
                self.bcc = await self.component.commander.readexactly(1)
                packet = packet.decode().strip()
                self.bcc = self.bcc.decode()

                if len(packet) < 16:
                    self.log.error(
                        f"Packet length is too small, minimum 16. Packet: {packet}"
                    )
                    # read bcc and return
                    await self.component.commander.readexactly(1)
                    return

                stx_node_subadd = packet[:5]
                expected_stx_node_subadd = "\x02"
                if int(self.node) < 10:
                    expected_stx_node_subadd += "\x30"
                expected_stx_node_subadd += self.node + "\x30\x30"

                if (
                    self.compare_string_values(
                        expected_stx_node_subadd, stx_node_subadd
                    )
                    is False
                ):
                    error_triggered = True
                self.end_code = packet[5:7]
                mrc_src = packet[7:11]
                # read variable area request MRC is 01, SRC is 01
                expected_mrc_src = "\x30\x31\x30\x31"

                if self.compare_string_values(expected_mrc_src, mrc_src) is False:
                    error_triggered = True

                self.response_code = packet[11:15]
                self.cmd_txt = packet[15:]
                self.cmd_txt = self.cmd_txt[:-1]

                try:
                    self.register_value = int(self.cmd_txt, 16)
                except Exception as e:
                    self.log.error(f"register_value conversion exception: {e}")
                    error_triggered = True

                # bcc should be calculated without STX, but with ETX byte
                bcc_frame = (
                    stx_node_subadd.split("\x02")[1]
                    + self.end_code
                    + mrc_src
                    + self.response_code
                    + self.cmd_txt
                    + "\x03"
                )

                expected_bcc = self.generate_bcc(bcc_frame)
                if expected_bcc is not self.bcc:
                    error_triggered = True

                if error_triggered:
                    self.log.error(
                        "Error triggered in read_register_value, dumping packet: "
                        f"packet: {packet}\n"
                        f"stx_node_subadd: {stx_node_subadd} "
                        f"expected: {expected_stx_node_subadd}\n"
                        f"mrc_src: {mrc_src} "
                        f"expected: {expected_mrc_src}\n"
                        f"register value: {self.register_value}\n"
                        f"bcc: {self.bcc} "
                        f"expected: {expected_bcc}"
                    )
                    self.log.error(f"ord BCC, expected: {ord(expected_bcc)}")
                    self.log.error(f"ord BCC, got: {ord(self.bcc)}")
            except Exception as e:
                self.log.error(
                    f"Message format not as expected. packet: {packet}, exception: {e}"
                )

    async def handle_set_response(self):
        async with self.component.lock:
            try:
                packet = await self.component.commander.readuntil(b"\x03")
                packet = packet.decode().strip()
                self.log.debug(
                    f"New set_register_value packet: {packet}, length: {len(packet)}"
                )
                if len(packet) < 15:
                    self.log.error("Packet length is too small, minimum 15")
                    # read bcc and return
                    await self.component.commander.readexactly(1)
                    return

                stx_node_subadd = packet[:5]
                expected_stx_node_subadd = "\x02"
                if int(self.node) < 10:
                    expected_stx_node_subadd += "\x30"
                expected_stx_node_subadd += self.node + "\x30\x30"

                if (
                    self.compare_string_values(
                        expected_stx_node_subadd, stx_node_subadd
                    )
                    is False
                ):
                    self.log.error(
                        f"Received incorrect start of packet: {stx_node_subadd}, "
                        f"expected: {expected_stx_node_subadd}"
                    )
                    self.register_value = -1

                self.end_code = packet[5:7]
                expected_end_code = "\x30\x30"

                if (
                    self.compare_string_values(expected_end_code, self.end_code)
                    is False
                ):
                    self.log.error(
                        f"Received bad end code: {self.end_code}: {self.end_code_dict[self.end_code]}"
                    )

                mrc_src = packet[7:11]
                # write variable area request MRC is 01, SRC is 02
                expected_mrc_src = "\x30\x31\x30\x32"

                if self.compare_string_values(expected_mrc_src, mrc_src) is False:
                    self.log.error(
                        f"Received incorrect Request Codes: {mrc_src}, "
                        f"expected: {expected_mrc_src}"
                    )
                self.response_code = packet[11:15]

                if (
                    self.compare_string_values("\x30\x30\x30\x30", self.response_code)
                    is False
                ):
                    self.log.error(
                        "Received bad response code: "
                        f"{self.response_code}: {self.response_dict[self.response_code]}"
                    )

                etx = packet[15:16]

                if self.compare_string_values("\x03", etx) is False:
                    self.log.error(f"Received bad ETX: {etx} expected: \x03")

                self.bcc = await self.component.commander.readexactly(1)
                self.bcc = self.bcc.decode()

                # bcc should be calculated without STX, but with ETX byte
                bcc_frame = (
                    stx_node_subadd.split("\x02")[1]
                    + self.end_code
                    + mrc_src
                    + self.response_code
                    + "\x03"
                )
                expected_bcc = self.generate_bcc(bcc_frame)
                if expected_bcc is not self.bcc:
                    self.log.error(
                        f"Incorrect BCC, got: {self.bcc}, expected: {expected_bcc}"
                    )
            except Exception as e:
                print(f"handle_set_response excepted: {e}")

    async def set_register_value(self, set_value):
        """Set the value of the register and read the new value.

        Parameters
        ----------
        set_value : Any

        Raises
        ------
        ReadOnlyException
            This indicates that the register is read only and cannot be set.
        ValueError
            If set value is too long (4 max)

        Returns
        -------
        None

        """
        if self.read_only:
            raise PermissionError("This register is read only.")
        if not self.simulation_mode:
            try:
                async with self.component.lock:
                    message = self.create_set_message(set_value)
                    self.log.debug(f"sending message {message}.")
                    await self.component.commander.write(
                        message.encode(self.component.commander.encoding)
                    )
                await self.handle_set_response()
                await self.read_register_value()
            except TimeoutError:
                self.log.exception("Response timed out.")
                raise
        else:
            self.register_value = set_value


class CompoWayFOperationRegister(CompoWayFGeneralRegister):
    """Specific operation register implementation using the CompoWayF standard.

    Parameters
    ----------
    component : `Laser`
        Reference to the component.
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

        # dictionary of implemented commands
        self.command_code_dict = {
            "Run Stop": "\x30\x31",
        }

        self.run_stop_related_info = {
            True: "\x30\x30",  # on
            False: "\x30\x31",  # off
            0: "\x30\x31",  # off
            1: "\x30\x30",  # on
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

    async def read_register_value(self):
        # can't read operational registers
        raise Exception("Can't read operational registers")

    async def handle_set_response(self):
        async with self.component.lock:
            try:
                packet = await self.component.commander.readuntil(b"\x03")
                packet = packet.decode().strip()
                self.log.debug(
                    f"New set_response packet: {packet}, length: {len(packet)}"
                )
                if len(packet) < 15:
                    self.log.error("Packet length is too small, minimum 15")
                    # read bcc and return
                    await self.component.commander.readexactly(1)
                    return

                stx_node_subadd = packet[:5]
                expected_stx_node_subadd = "\x02"
                if int(self.node) < 10:
                    expected_stx_node_subadd += "\x30"
                expected_stx_node_subadd += self.node + "\x30\x30"

                if (
                    self.compare_string_values(
                        expected_stx_node_subadd, stx_node_subadd
                    )
                    is False
                ):
                    self.log.error(
                        f"Received incorrect start of packet: {stx_node_subadd}, "
                        f"expected: {expected_stx_node_subadd}"
                    )
                    self.register_value = -1

                self.end_code = packet[5:7]
                if self.compare_string_values("\x30\x30", self.end_code) is False:
                    self.log.error(
                        f"Received bad end code: {self.end_code}: {self.end_code_dict[self.end_code]}"
                    )

                mrc_src = packet[7:11]
                # write variable area request MRC is 30, SRC is 05
                expected_mrc_src = "\x33\x30\x30\x35"
                if self.compare_string_values(expected_mrc_src, mrc_src) is False:
                    self.log.error(
                        f"Received incorrect Request Codes: {mrc_src}, "
                        f"expected: {expected_mrc_src}"
                    )
                self.response_code = packet[11:15]

                if (
                    self.compare_string_values("\x30\x30\x30\x30", self.response_code)
                    is False
                ):
                    self.log.error(
                        "Received bad response code: "
                        f"{self.response_code}: {self.response_dict[self.response_code]}"
                    )

                etx = packet[15:16]

                if self.compare_string_values("\x03", etx) is False:
                    self.log.error(f"Received bad ETX: {etx} expected: \x03")

                self.bcc = await self.component.commander.readexactly(1)
                self.bcc = self.bcc.decode()

                # bcc should be calculated without STX, but with ETX byte
                bcc_frame = (
                    stx_node_subadd.split("\x02")[1]
                    + self.end_code
                    + mrc_src
                    + self.response_code
                    + "\x03"
                )
                expected_bcc = self.generate_bcc(bcc_frame)
                if expected_bcc is not self.bcc:
                    self.log.error(
                        f"Incorrect BCC, got: {self.bcc}, expected: {expected_bcc}"
                    )
            except Exception as e:
                print(f"handle_set_response excepted: {e}")

    def get_related_info(self, set_value):
        chosen_dict = None
        # RUN/STOP
        if self.command_code == "\x30\x31":
            chosen_dict = self.run_stop_related_info
        else:
            self.log.error(
                f"No valid command code in get_related_info: {self.command_code}"
            )
        if set_value in chosen_dict:
            return chosen_dict[set_value]
        else:
            self.log.error(f"No set value ({set_value}) in chosen dict ({chosen_dict})")
            return None

    async def set_register_value(self, set_value):
        """Set the value of the register.

        Parameters
        ----------
        set_value : Any

        Raises
        ------
        PermissionError
            This indicates that the register is read only and cannot be set.
        TimeoutError
            Response timed out.
        ValueError
            selected value not found in related info dictionary

        Returns
        -------
        None

        """
        if self.read_only:
            raise PermissionError("This register is read only.")
        try:
            async with self.component.lock:
                message = self.create_set_message(set_value)
                self.log.debug(f"sending message {message}.")
                if self.simulation_mode:
                    message += "\r"
                await self.component.commander.write(
                    message.encode(self.component.commander.encoding)
                )
            await self.handle_set_response()
        except TimeoutError:
            self.log.exception("Response timed out.")
            raise TimeoutError
        self.register_value = set_value
