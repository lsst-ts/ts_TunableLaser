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

import asyncio
import logging
import unittest
import unittest.mock

from lsst.ts.tunablelaser.canbus_modules import CPU8000, MaxiOPG
from lsst.ts.tunablelaser.interfaces import Laser


class FakeLaser(Laser):
    def __init__(self):
        super().__init__(log=logging.getLogger(__name__), terminator=b"\r", encoding="ascii")
        self.cpu8000 = CPU8000()
        self.maxi_opg = MaxiOPG()

    @property
    def is_propagating(self):
        return False

    @property
    def wavelength(self):
        return self.maxi_opg.wavelength_register.register_value

    @property
    def temperature(self):
        return ()

    @property
    def propagation_mode(self):
        return None

    @property
    def optical_configuration(self):
        return self.maxi_opg.configuration_register.register_value

    async def change_wavelength(self, wavelength):
        raise NotImplementedError

    async def set_output_energy_level(self, output_energy_level):
        raise NotImplementedError

    async def trigger_burst(self):
        raise NotImplementedError

    async def set_burst_mode(self, count):
        raise NotImplementedError

    async def start_propagating(self):
        raise NotImplementedError

    async def stop_propagating(self):
        raise NotImplementedError

    async def clear_fault(self):
        raise NotImplementedError

    async def configure(self, config):
        raise NotImplementedError


class TestCPU8000(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.cpu8000 = CPU8000()

    async def test_update_register(self):
        values = iter(["ON", "19A", "0"])

        async def read_register(register):
            register.register_value = next(values)
            return register.register_value

        await self.cpu8000.update_register(read_register)

        self.assertEqual(self.cpu8000.power_register.register_value, "ON")
        self.assertEqual(self.cpu8000.display_current_register.register_value, "19A")
        self.assertEqual(self.cpu8000.fault_register.register_value, "0")

    def test_repr(self):
        assert repr(self.cpu8000) == "CPU8000:\n Power: None\n Display Current: None\n Fault code: None\n"


class TestMaxiOPG(unittest.IsolatedAsyncioTestCase):
    def test_scu_configuration(self):
        self.maxiopg = MaxiOPG()
        assert self.maxiopg.configuration_register.accepted_values == [
            "SCU",
            "F1 SCU",
            "F2 SCU",
            "No SCU",
            "F1 No SCU",
            "F2 No SCU",
        ]


class TestLaserRegisterRefresh(unittest.IsolatedAsyncioTestCase):
    async def test_refresh_all_ascii_registers_does_not_shift_values_between_registers(self):
        laser = FakeLaser()
        laser.commander = unittest.mock.AsyncMock()
        laser.commander.encoding = "ascii"
        laser.commander.write = unittest.mock.AsyncMock()
        laser.commander.read_str = unittest.mock.AsyncMock(side_effect=["ON", "19A", "0", "700nm", "SCU"])

        await laser.refresh_all_ascii_registers()

        self.assertEqual(laser.cpu8000.power_register.register_value, "ON")
        self.assertEqual(laser.cpu8000.display_current_register.register_value, "19A")
        self.assertEqual(laser.cpu8000.fault_register.register_value, "0")
        self.assertEqual(laser.maxi_opg.wavelength_register.register_value, "700")
        self.assertEqual(laser.maxi_opg.configuration_register.register_value, "SCU")

        written_messages = [call.args[0].decode("ascii") for call in laser.commander.write.await_args_list]
        self.assertEqual(
            written_messages,
            [
                "/CPU8000/16/Power\r",
                "/CPU8000/16/Display Current\r",
                "/CPU8000/16/Fault code\r",
                "/MaxiOPG/31/WaveLength\r",
                "/MaxiOPG/31/Configuration\r",
            ],
        )

    async def test_concurrent_read_register_calls_are_serialized_by_lock(self):
        class TrackingCommander:
            def __init__(self, responses):
                self.encoding = "ascii"
                self._responses = iter(responses)
                self.writes = []
                self.in_flight = 0
                self.max_in_flight = 0

            async def write(self, data):
                self.writes.append(data.decode("ascii"))
                self.in_flight += 1
                self.max_in_flight = max(self.max_in_flight, self.in_flight)
                await asyncio.sleep(0.01)

            async def read_str(self):
                await asyncio.sleep(0.01)
                response = next(self._responses)
                self.in_flight -= 1
                return response

        laser = FakeLaser()
        laser.commander = TrackingCommander(["ON", "19A"])

        await asyncio.gather(
            laser.read_register(laser.cpu8000.power_register),
            laser.read_register(laser.cpu8000.display_current_register),
        )

        self.assertEqual(laser.commander.max_in_flight, 1)
        self.assertEqual(laser.cpu8000.power_register.register_value, "ON")
        self.assertEqual(laser.cpu8000.display_current_register.register_value, "19A")
        self.assertEqual(
            laser.commander.writes,
            [
                "/CPU8000/16/Power\r",
                "/CPU8000/16/Display Current\r",
            ],
        )

    async def test_read_register_raises_on_triple_quote_error_response(self):
        laser = FakeLaser()
        laser.commander = unittest.mock.AsyncMock()
        laser.commander.encoding = "ascii"
        laser.commander.write = unittest.mock.AsyncMock()
        laser.commander.read_str = unittest.mock.AsyncMock(
            return_value="'''Error: (8) Timeout waiting for device answer"
        )

        with self.assertRaisesRegex(RuntimeError, "failed"):
            await laser.read_register(laser.cpu8000.power_register)

        self.assertIsNone(laser.cpu8000.power_register.register_value)

    async def test_write_register_raises_on_triple_quote_error_response(self):
        laser = FakeLaser()
        laser.commander = unittest.mock.AsyncMock()
        laser.commander.encoding = "ascii"
        laser.commander.write = unittest.mock.AsyncMock()
        laser.commander.read_str = unittest.mock.AsyncMock(
            return_value="'''Error: (11) Violating top value limit"
        )

        with self.assertRaisesRegex(RuntimeError, "failed"):
            await laser.write_register(laser.maxi_opg.wavelength_register, 700)

        self.assertIsNone(laser.maxi_opg.wavelength_register.register_value)
