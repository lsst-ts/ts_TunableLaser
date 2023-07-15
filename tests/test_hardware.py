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
from lsst.ts.tunablelaser.hardware import CPU8000, MaxiOPG


class TestCPU8000(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.cpu8000 = CPU8000(None)

    async def test_update_register(self):
        self.cpu8000.commander = unittest.mock.AsyncMock()
        self.cpu8000.commander.send_command = unittest.mock.AsyncMock()
        self.cpu8000.power_register.commander = unittest.mock.AsyncMock()
        self.cpu8000.display_current_register.commander = unittest.mock.AsyncMock()
        self.cpu8000.fault_register.commander = unittest.mock.AsyncMock()
        await self.cpu8000.update_register()

    def test_repr(self):
        assert (
            repr(self.cpu8000)
            == "CPU8000:\n Power: None\n Display Current: None\n Fault code: None\n"
        )


class TestMaxiOPG(unittest.IsolatedAsyncioTestCase):
    def test_scu_configuration(self):
        self.maxiopg = MaxiOPG(None, configuration="SCU")
        assert self.maxiopg.configuration_register.accepted_values == [
            "SCU",
            "F1 SCU",
            "F2 SCU",
        ]
        self.maxiopg = MaxiOPG(None)
        assert self.maxiopg.configuration_register.accepted_values == [
            "No SCU",
            "F1 No SCU",
            "F2 No SCU",
        ]

    def test_invalid_configuration(self):
        with pytest.raises(ValueError):
            self.maxiopg = MaxiOPG(None, configuration="wumbo")
