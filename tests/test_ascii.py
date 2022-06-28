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

from lsst.ts.tunablelaser.ascii import AsciiRegister


class TestAsciiRegister(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.ascii_register = AsciiRegister(
            commander=None, module_name="Test", module_id=0, register_name="Test"
        )
        self.settable_ascii_register = AsciiRegister(
            commander=None,
            module_name="Foo",
            module_id=0,
            register_name="Bar",
            read_only=False,
            accepted_values=range(0, 10),
        )
        self.simulation_ascii_register = AsciiRegister(
            commander=None,
            module_name="Fake",
            module_id=0,
            register_name="Register",
            read_only=True,
            simulation_mode=True,
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
                commander=None,
                module_name="Bad",
                module_id=0,
                register_name="Bad",
                read_only=False,
            )

    async def test_read_register_value(self):
        self.ascii_register.create_get_message = unittest.mock.Mock(
            return_value="/Test/0/Test\r"
        )
        self.ascii_register.commander = unittest.mock.Mock()
        self.ascii_register.commander.send_command = unittest.mock.AsyncMock(
            return_value="ON"
        )
        await self.ascii_register.read_register_value()
        assert self.ascii_register.register_value == "ON"
        with pytest.raises(TimeoutError):
            self.ascii_register.create_get_message = unittest.mock.Mock(
                return_value="/Test/0/Test\r"
            )
            self.ascii_register.commander = unittest.mock.Mock()
            self.ascii_register.commander.send_command = unittest.mock.AsyncMock(
                return_value=None
            )
            await self.ascii_register.read_register_value()

    async def test_set_register_value(self):
        with pytest.raises(PermissionError):
            await self.ascii_register.set_register_value(5)
        self.settable_ascii_register.create_set_message = unittest.mock.Mock(
            return_value="/Foo/0/Bar/5\r"
        )
        self.settable_ascii_register.commander = unittest.mock.Mock()
        self.settable_ascii_register.commander.send_command = unittest.mock.AsyncMock()
        await self.settable_ascii_register.set_register_value(5)
        with pytest.raises(TimeoutError):
            self.settable_ascii_register.create_set_message = unittest.mock.Mock(
                return_value="/Foo/0/Bar/5\r"
            )
            self.settable_ascii_register.commander = unittest.mock.Mock()
            self.settable_ascii_register.commander.send_command = (
                unittest.mock.AsyncMock(side_effect=TimeoutError)
            )
            await self.settable_ascii_register.set_register_value(5)
        self.simulation_ascii_register.read_only = False
        await self.simulation_ascii_register.set_register_value(5)
        assert self.simulation_ascii_register.register_value == 5

    def test_repr(self):
        assert repr(self.ascii_register) == "Test: None"
