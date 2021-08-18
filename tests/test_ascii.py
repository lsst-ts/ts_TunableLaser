import unittest
import unittest.mock

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
        self.assertEqual(msg, "/Test/0/Test\r")

    def test_create_set_message(self):
        with self.assertRaises(PermissionError):
            self.ascii_register.create_set_message(set_value=5)
        with self.subTest("Test writable register"):
            msg = self.settable_ascii_register.create_set_message(5)
            self.assertEqual(msg, "/Foo/0/Bar/5\r")
        with self.subTest("Test value outside of range"):
            with self.assertRaises(ValueError):
                self.settable_ascii_register.create_set_message(15)
        with self.subTest("Test lack of accepted values"):
            with self.assertRaises(AttributeError):
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
        self.assertEqual(self.ascii_register.register_value, "ON")
        with self.subTest("Check timeout handling"):
            with self.assertRaises(TimeoutError):
                self.ascii_register.create_get_message = unittest.mock.Mock(
                    return_value="/Test/0/Test\r"
                )
                self.ascii_register.commander = unittest.mock.Mock()
                self.ascii_register.commander.send_command = unittest.mock.AsyncMock(
                    return_value=None
                )
                await self.ascii_register.read_register_value()

    async def test_set_register_value(self):
        with self.assertRaises(PermissionError):
            await self.ascii_register.set_register_value(5)
        with self.subTest("Check writable register"):
            self.settable_ascii_register.create_set_message = unittest.mock.Mock(
                return_value="/Foo/0/Bar/5\r"
            )
            self.settable_ascii_register.commander = unittest.mock.Mock()
            self.settable_ascii_register.commander.send_command = (
                unittest.mock.AsyncMock()
            )
            await self.settable_ascii_register.set_register_value(5)
        with self.subTest("Check timeout handling"):
            with self.assertRaises(TimeoutError):
                self.settable_ascii_register.create_set_message = unittest.mock.Mock(
                    return_value="/Foo/0/Bar/5\r"
                )
                self.settable_ascii_register.commander = unittest.mock.Mock()
                self.settable_ascii_register.commander.send_command = (
                    unittest.mock.AsyncMock(side_effect=TimeoutError)
                )
                await self.settable_ascii_register.set_register_value(5)
        with self.subTest("Check simulation mode handling"):
            self.simulation_ascii_register.read_only = False
            await self.simulation_ascii_register.set_register_value(5)
            self.assertEqual(self.simulation_ascii_register.register_value, 5)

    def test_repr(self):
        self.assertEqual(repr(self.ascii_register), "Test: None")
