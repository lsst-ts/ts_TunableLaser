import unittest

from lsst.ts.tunablelaser.ascii import AsciiSerial, AsciiError, AsciiRegister, ReadOnlyException


class TestAsciiSerial(unittest.TestCase):
    def setUp(self):
        self.ascii_serial = AsciiSerial(None)

    def test_perform_magic(self):
        self.ascii_serial.write = unittest.mock.Mock()
        self.ascii_serial.read_until = unittest.mock.Mock()
        self.ascii_serial.parse_reply = unittest.mock.Mock(return_value="525")
        reply = self.ascii_serial.perform_magic(b"/MaxiOPG/31/Wavelength\r")
        self.assertEqual(reply, "525")
        with self.subTest("Check timeout handling"):
            self.ascii_serial.write = unittest.mock.Mock()
            self.ascii_serial.read_until = unittest.mock.Mock(side_effect=TimeoutError)
            self.ascii_serial.flush = unittest.mock.Mock()
            reply = self.ascii_serial.perform_magic(b"/MaxiOPG/31/WaveLength\r")
            self.assertEqual(reply, None)
        with self.subTest("Check Exception handling"):
            with self.assertRaises(Exception):
                self.ascii_serial.write = unittest.mock.Mock(side_effect=Exception)
                self.ascii_serial.read_until = unittest.mock.Mock()
                self.ascii_serial.perform_magic(b"/MaxiOPG/31/WaveLength\r")

    def test_parse_reply(self):
        reply = self.ascii_serial.parse_reply(b"525nm\r\n\x03")
        self.assertEqual(reply, "525")
        with self.subTest("Check ascii error handling"):
            with self.assertRaises(AsciiError):
                self.ascii_serial.parse_reply(b"'''17 unexpected character")


class TestAsciiRegister(unittest.TestCase):
    def setUp(self):
        self.ascii_register = AsciiRegister(port=None,
                                            module_name="Test",
                                            module_id=0,
                                            register_name="Test")
        self.settable_ascii_register = AsciiRegister(port=None,
                                                     module_name="Foo",
                                                     module_id=0,
                                                     register_name="Bar",
                                                     read_only=False,
                                                     accepted_values=range(0, 10))
        self.bad_settable_ascii_register = AsciiRegister(port=None,
                                                         module_name="Bad",
                                                         module_id=0,
                                                         register_name="Bad",
                                                         read_only=False)
        self.simulation_ascii_register = AsciiRegister(port=None,
                                                       module_name="Fake",
                                                       module_id=0,
                                                       register_name="Register",
                                                       read_only=False,
                                                       simulation_mode=True)

    def test_create_get_message(self):
        msg = self.ascii_register.create_get_message()
        self.assertEqual(msg, b"/Test/0/Test\r")

    def test_create_set_message(self):
        with self.assertRaises(ReadOnlyException):
            self.ascii_register.create_set_message(set_value=5)
        with self.subTest("Test writable register"):
            msg = self.settable_ascii_register.create_set_message(5)
            self.assertEqual(msg, b"/Foo/0/Bar/5\r")
        with self.subTest("Test value outside of range"):
            with self.assertRaises(ValueError):
                self.settable_ascii_register.create_set_message(15)
        with self.subTest("Test lack of accepted values"):
            with self.assertRaises(AttributeError):
                self.bad_settable_ascii_register.create_set_message(5)

    def test_get_register_value(self):
        self.ascii_register.create_get_message = unittest.mock.Mock(return_value=b"/Test/0/Test\r")
        self.ascii_register.port = unittest.mock.Mock()
        self.ascii_register.port.perform_magic = unittest.mock.Mock(return_value="ON")
        self.ascii_register.get_register_value()
        self.assertEqual(self.ascii_register.register_value, "ON")
        with self.subTest("Check timeout handling"):
            with self.assertRaises(TimeoutError):
                self.ascii_register.create_get_message = unittest.mock.Mock(return_value=b"/Test/0/Test\r")
                self.ascii_register.port = unittest.mock.Mock()
                self.ascii_register.port.perform_magic = unittest.mock.Mock(return_value=None)
                self.ascii_register.get_register_value()
        with self.subTest("Check simulation mode handling"):
            self.simulation_ascii_register.get_register_value()
            self.assertTrue(17.8 <= self.simulation_ascii_register.register_value <= 18.2)
        with self.subTest("Check read only simulation mode handling"):
            self.simulation_ascii_register.read_only = True
            self.simulation_ascii_register.get_register_value()

    def test_set_register_value(self):
        with self.assertRaises(ReadOnlyException):
            self.ascii_register.set_register_value(5)
        with self.subTest("Check writable register"):
            self.settable_ascii_register.create_set_message = unittest.mock.Mock(
                return_value=b"/Foo/0/Bar/5\r")
            self.settable_ascii_register.port = unittest.mock.Mock()
            self.settable_ascii_register.port.perform_magic = unittest.mock.Mock()
            self.settable_ascii_register.set_register_value(5)
        with self.subTest("Check timeout handling"):
            with self.assertRaises(TimeoutError):
                self.settable_ascii_register.create_set_message = unittest.mock.Mock(
                    return_value=b"/Foo/0/Bar/5\r")
                self.settable_ascii_register.port = unittest.mock.Mock()
                self.settable_ascii_register.port.perform_magic = unittest.mock.Mock(side_effect=TimeoutError)
                self.settable_ascii_register.set_register_value(5)
        with self.subTest("Check simulation mode handling"):
            self.simulation_ascii_register.set_register_value(5)
            self.assertEqual(self.simulation_ascii_register.register_value, 5)

    def test_str(self):
        self.assertEqual(str(self.ascii_register), "Test: None")
