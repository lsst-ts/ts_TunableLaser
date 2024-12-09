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
from lsst.ts.tunablelaser.register import AsciiRegister


@pytest.mark.skip()
class TestAsciiRegister(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.ascii_register = AsciiRegister(
            component=unittest.mock.AsyncMock(),
            module_name="Test",
            module_id=0,
            register_name="Test",
        )
        self.settable_ascii_register = AsciiRegister(
            component=unittest.mock.AsyncMock(),
            module_name="Foo",
            module_id=0,
            register_name="Bar",
            read_only=False,
            accepted_values=range(0, 10),
        )

    def test_create_get_message(self):
        msg = self.ascii_register.create_get_message()
        assert msg == "/Test/0/Test\r"

    def test_create_set_message(self):
        with pytest.raises(PermissionError):
            self.ascii_register.create_set_message(set_value=5)
        msg = self.settable_ascii_register.create_set_message(5)
        assert msg == "/Foo/0/Bar/5\r"
        with pytest.raises(ValueError):
            self.settable_ascii_register.create_set_message(15)
        with pytest.raises(AttributeError):
            self.bad_settable_ascii_register = AsciiRegister(
                component=None,
                module_name="Bad",
                module_id=0,
                register_name="Bad",
                read_only=False,
            )

    async def test_read_register_value(self):
        self.ascii_register.create_get_message = unittest.mock.Mock(
            return_value="/Test/0/Test\r"
        )
        self.ascii_register.component.commander.encoding = "ascii"
        self.ascii_register.component.commander.send_command = unittest.mock.AsyncMock(
            return_value="ON"
        )
        self.ascii_register.component.commander.read_str = unittest.mock.AsyncMock(
            return_value="ON"
        )
        await self.ascii_register.send_command()
        assert self.ascii_register.register_value == "ON"
        with pytest.raises(TimeoutError):
            self.ascii_register.create_get_message = unittest.mock.Mock(
                return_value="/Test/0/Test\r"
            )
            self.ascii_register.component.commander.send_command = (
                unittest.mock.AsyncMock(return_value=None)
            )
            self.ascii_register.component.commander.read_str = unittest.mock.AsyncMock(
                return_value=None
            )
            await self.ascii_register.send_command()

    # @pytest.mark.skip("Not working.")
    async def test_set_register_value(self):
        with pytest.raises(PermissionError):
            await self.ascii_register.send_command(5)
        self.settable_ascii_register.create_set_message = unittest.mock.Mock(
            return_value="/Foo/0/Bar/5\r"
        )
        self.settable_ascii_register.component.commander.encoding = "ascii"
        self.settable_ascii_register.component.commander.send_command = (
            unittest.mock.AsyncMock()
        )
        await self.settable_ascii_register.send_command(5)
        with pytest.raises(TimeoutError):
            self.settable_ascii_register.create_set_message = unittest.mock.Mock(
                return_value="/Foo/0/Bar/5\r"
            )
            self.settable_ascii_register.component.commander.send_command = (
                unittest.mock.AsyncMock(side_effect=TimeoutError)
            )
            self.settable_ascii_register.component.commander.read_str = (
                unittest.mock.AsyncMock(return_value=None)
            )
            await self.settable_ascii_register.send_command(5)

    def test_repr(self):
        assert repr(self.ascii_register) == "Test: None"
