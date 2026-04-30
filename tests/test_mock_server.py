import unittest

from lsst.ts.tunablelaser.canbus import pgd217_nt252
from lsst.ts.tunablelaser.enums import Mode, Output, Power
from lsst.ts.tunablelaser.mock_server import (
    MockMessage,
    MockNP5450,
    MockNT252,
    MockNT900,
)


class TestMockMessage(unittest.TestCase):
    def test_bad_message(self):
        with self.assertRaises(Exception):
            MockMessage(b"xdfgghtb")


class TestMockNT252(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.device = MockNT252()
        self.device.wavelength = 532
        self.device.cpu8000_power = Power.ON
        self.device.m_cpu800_power = Power.ON
        self.device.propagating = Power.OFF
        self.device.output_energy_level = Output.ADJUST
        self.device.propagation_mode = Mode.CONTINUOUS
        self.device.cpu8000_current = "0.5"
        self.device.m_cpu800_current = "0.8"
        self.device.frequency_divider = 1
        self.device.qsw_adjustment_output_delay = 308
        self.device.repetition_rate = 1000
        self.device.burst_length = 1
        self.device.synchronization_mode = "Internal"
        self.device.diode_current_on = "ON"
        self.device.external_interlock_state = "Defeated"
        self.device.ph532_power = "0.002"
        self.device.ldco48bp_48_temperature = "31.00"
        self.device.ldco48bp_50_temperature = "28.00"
        self.device.tk6_44_temperature = "50.00"
        self.modules = [getattr(pgd217_nt252, name)() for name in pgd217_nt252.__all__]

    def _strip_terminator(self, message):
        return message.rstrip("\r")

    def _pick_write_value(self, register):
        accepted_values = register.accepted_values
        if isinstance(accepted_values, range):
            if len(accepted_values) > 1:
                return accepted_values.start + accepted_values.step
            return accepted_values.start
        accepted_values = list(accepted_values)
        if len(accepted_values) > 1:
            return accepted_values[1]
        return accepted_values[0]

    def _expected_readback(self, register, value):
        if register.register_name == "WaveLength":
            return f"{value}nm"
        return str(value)

    def test_generated_stubbs_read_commands_return_expected_values(self):
        expected = {
            "/M_CPU800/18/Power": "OFF",
            "/M_CPU800/18/Diode current ON": "ON",
            "/M_CPU800/18/Output Energy level": "Adjust",
            "/M_CPU800/18/Continuous %2f Burst mode %2f Trigger burst": "Continuous",
            "/M_CPU800/18/QSW Adjustment output delay": "308",
            "/M_CPU800/18/Frequency divider": "1",
            "/M_CPU800/18/Burst length": "1",
            "/M_CPU800/18/Synchronization mode": "Internal",
            "/M_CPU800/18/Repetition rate": "1000",
            "/M_CPU800/18/External interlock state": "Defeated",
            "/M_CPU800/17/Power": "ON",
            "/M_CPU800/17/Display Current": "0.8",
            "/PH_532/55/Power": "0.002",
            "/MidiOPG/31/WaveLength": "532nm",
            "/MidiOPG/31/Status": "Ok.",
            "/LDCO48BP/48/Set temperature": "31.00",
            "/LDCO48BP/50/Set temperature": "28.00",
            "/LDCO48BP/50/Display temperature": "28.00",
            "/LDCO48BP/48/Display temperature": "31.00",
            "/LDCO48BP/28/Error Code": "0",
            "/LDCO48BP/29/Error Code": "0",
            "/TK6/44/Set temperature": "50.00",
            "/TK6/44/Display temperature": "50.00",
            "/CPU8000/16/Power": "ON",
            "/CPU8000/16/Display Current": "0.5",
            "/M_LDCO48/33/Error Code": "0",
            "/M_LDCO48/34/Error Code": "0",
            "/HV40W/40/Error Code": "0",
            "/FOPO/51/Error Code": "0",
            "/SOPO/52/Error Code": "0",
            "/SH1/53/Error Code": "0",
            "/C1/54/Error Code": "0",
        }

        actual_commands = {
            self._strip_terminator(register.create_get_message())
            for module in self.modules
            for register in module.iter_ascii_registers()
        }
        self.assertEqual(actual_commands, set(expected))

        for command, expected_value in expected.items():
            with self.subTest(command=command):
                self.assertEqual(self.device.parse_message(command), expected_value)

    def test_generated_stubbs_accepted_values_match_writable_vendor_ranges(self):
        expected = {
            "/M_CPU800/18/Power": ["OFF", "ON"],
            "/M_CPU800/18/Diode current ON": ["OFF", "ON"],
            "/M_CPU800/18/Output Energy level": ["OFF", "Adjust", "MAX"],
            "/M_CPU800/18/Continuous %2f Burst mode %2f Trigger burst": [
                "Continuous",
                "Burst",
                "Trigger",
            ],
            "/M_CPU800/18/Synchronization mode": ["Internal", "External"],
            "/M_CPU800/17/Power": ["OFF", "ON"],
            "/CPU8000/16/Power": ["OFF", "ON"],
        }

        actual = {
            self._strip_terminator(register.create_get_message()): register.accepted_values
            for module in self.modules
            for register in module.iter_ascii_registers()
            if not register.read_only and not isinstance(register.accepted_values, range)
        }
        self.assertEqual(actual, expected)

    def test_generated_stubbs_writable_commands_round_trip(self):
        for module in self.modules:
            for register in module.iter_ascii_registers():
                if register.read_only:
                    continue

                value = self._pick_write_value(register)
                set_command = self._strip_terminator(register.create_set_message(value))
                get_command = self._strip_terminator(register.create_get_message())

                with self.subTest(command=set_command):
                    self.assertEqual(self.device.parse_message(set_command), "")
                    self.assertEqual(
                        self.device.parse_message(get_command),
                        self._expected_readback(register, value),
                    )


class TestMockNT900(unittest.TestCase):
    def test_check_limits(self):
        device = MockNT900()
        reply = device.check_limits(200, 300, 1100)
        self.assertEqual(reply, "'''Error: (12) Violating bottom value limit")
        reply = device.check_limits(1200, 300, 1100)
        self.assertEqual(reply, "'''Error: (11) Violating top value limit")

    def test_do_change_continuous_burst_mode_trigger_burst(self):
        device = MockNT900()
        reply = device.do_set_m_cpu800_18_continuous_burst_mode_trigger_burst("wumbo")
        self.assertEqual(reply, "'''Error: (13) Wrong value, not included in allowed values list")


class TestMockNP5450(unittest.TestCase):
    def test_reply(self):
        device = MockNP5450()
        device.e5dcb_setpoint_temperature = 56
        reply = device.do_get_01_sp()
        self.assertEqual(reply, "\x020100000101000056\x03\x01")
