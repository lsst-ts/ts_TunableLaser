import unittest.mock

from lsst.ts.tunablelaser.hardware import CPU8000


class TestCPU8000(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.cpu8000 = CPU8000(None)
        self.sim_cpu8000 = CPU8000(None, True)

    async def test_update_register(self):
        self.cpu8000.commander = unittest.mock.AsyncMock()
        self.cpu8000.commander.send_command = unittest.mock.AsyncMock()
        self.cpu8000.power_register.commander = unittest.mock.AsyncMock()
        self.cpu8000.display_current_register.commander = unittest.mock.AsyncMock()
        self.cpu8000.fault_register.commander = unittest.mock.AsyncMock()
        await self.cpu8000.update_register()

    def test_set_simulation_mode(self):
        self.cpu8000.set_simulation_mode(True)
        self.assertEqual(self.cpu8000.power_register.simulation_mode, True)
        self.assertEqual(self.cpu8000.display_current_register.simulation_mode, True)
        self.assertEqual(self.cpu8000.fault_register.simulation_mode, True)
        with self.subTest("Test going out of simulation mode"):
            self.sim_cpu8000.set_simulation_mode(False)
            self.assertEqual(self.sim_cpu8000.power_register.simulation_mode, False)
            self.assertEqual(
                self.sim_cpu8000.display_current_register.simulation_mode, False
            )
            self.assertEqual(self.sim_cpu8000.fault_register.simulation_mode, False)

    def test_repr(self):
        self.assertEqual(
            repr(self.cpu8000),
            "CPU8000:\n Power: None\n Display Current: None\n Fault code: None\n",
        )
