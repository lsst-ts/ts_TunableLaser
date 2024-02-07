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

import unittest
import unittest.mock

import pytest
from lsst.ts.tunablelaser.compoway_register import (
    CompoWayFDataRegister,
    CompoWayFGeneralRegister,
    CompoWayFOperationRegister,
)


class TestAsciiRegister(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.STX = "\x02"
        self.ETX = "\x03"

        self.general_register = CompoWayFGeneralRegister(
            component=unittest.mock.AsyncMock(),
            module_name="GenTest",
            module_id=1,
            register_name="GenTestRegister",
        )

        self.data_register = CompoWayFDataRegister(
            component=unittest.mock.AsyncMock(),
            module_name="DataTest",
            module_id=2,
            register_name="Set Point",
            read_only=False,
            accepted_values=range(101),
        )

        self.read_only_data_reg = CompoWayFDataRegister(
            component=unittest.mock.AsyncMock(),
            module_name="DataTest",
            module_id=2,
            register_name="Set Point",
            read_only=True,
        )

        self.operation_register = CompoWayFOperationRegister(
            component=unittest.mock.AsyncMock(),
            module_name="OpTest",
            module_id=3,
            register_name="Run Stop",
            accepted_values=range(0, 2),
        )

    def test_bcc(self):
        # taken from E5DCB communications doc page 33
        # section 2-1-2
        frame = "\x30\x30\x30\x30\x30\x30\x35\x30\x33\x03"
        assert self.general_register.generate_bcc(frame) == "\x35"

    def test_cmd_frame(self):
        pdu_structure = "TEST"
        correct_frame = "\x30\x31\x30\x30\x30" + pdu_structure + self.ETX
        bcc = self.general_register.generate_bcc(correct_frame)
        correct_frame = self.STX + correct_frame + bcc

        test_frame = self.general_register.compoway_cmd_frame(pdu_structure)
        assert correct_frame == test_frame

    async def test_generic_message_exceptions(self):
        # user should never use the general register class for messaging
        with pytest.raises(Exception):
            self.general_register.create_get_message()
            self.general_register.create_set_message()
            await self.general_register.read_register_value()
            await self.general_register.set_register_value()

            self.operation_register.create_get_message()
            await self.operation_register.read_register_value()

    def test_class_creation(self):
        with pytest.raises(ValueError):
            CompoWayFDataRegister(
                component=unittest.mock.AsyncMock(),
                module_name="DataTest",
                module_id=2,
                register_name="Invalid Register",
            )
            CompoWayFOperationRegister(
                component=unittest.mock.AsyncMock(),
                module_name="OpTest",
                module_id=3,
                register_name="Invalid Register",
                accepted_values=range(0, 2),
            )
            CompoWayFDataRegister(
                component=unittest.mock.AsyncMock(),
                module_name="DataTest",
                module_id=2,
                register_name="Invalid Register",
                read_only=False,
            )

    def test_create_get_message(self):
        msg = self.data_register.create_get_message()
        assert msg == "\x02020000101810003000001\x03:"

    def test_create_set_message(self):
        with pytest.raises(PermissionError):
            self.read_only_data_reg.create_set_message(set_value=5)
        with pytest.raises(ValueError):
            self.data_register.create_set_message(set_value=50000)

        msg = self.data_register.create_set_message(5)
        assert msg == "\x020200001028100030000015\x03\x0c"

        msg = self.operation_register.create_set_message(1)
        assert msg == "\x02030003005811\x03\x0e"

    def test_repr(self):
        assert repr(self.data_register) == "Set Point: None"
        assert repr(self.operation_register) == "Run Stop: None"
