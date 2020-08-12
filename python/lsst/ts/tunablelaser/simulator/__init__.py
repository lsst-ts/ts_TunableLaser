from lewis.devices import StateMachineDevice

from lewis.core.statemachine import State

from collections import OrderedDict

from lewis.adapters.stream import StreamInterface, Cmd, scanf


class CPU8000:
    def __init__(self):
        self._power = "ON"
        self._display_current = 1.5
        self._fault = "0h"
        self.id = 16

    @property
    def power(self):
        return self._power

    @property
    def display_current(self):
        return str(self._display_current) + "A"

    @property
    def fault(self):
        return self._fault


class MCPU800:
    def __init__(self):
        self.id = 17
        self.id_2 = 18
        self._power = "ON"
        self._display_current = 1.5
        self._fault = "0h"
        self._power_2 = "OFF"
        self._display_current_2 = 0.4
        self._fault_2 = "0h"
        self._continuous_burst_mode_trigger_burst = "Continuous"
        self._output_energy_level = "OFF"
        self._frequency_divider = 1
        self._burst_pulse_left = 0
        self._qsw_adjustment_output_delay = 0
        self._repetition_rate = 0
        self._synchronization_mode = 0
        self._burst_length = 1

    @property
    def power(self):
        return self._power

    @property
    def display_current(self):
        return self._display_current

    @property
    def fault(self):
        return self._fault

    @property
    def power_2(self):
        return self._power_2

    @power_2.setter()
    def power_2(self, new_power):
        if new_power in ["OFF", "ON"]:
            self._power_2 = new_power

    @property
    def continuous_burst_mode_trigger_burst(self):
        return self._continuous_burst_mode_trigger_burst

    @property
    def output_energy_level(self):
        return self._output_energy_level

    @property
    def frequency_divider(self):
        return self._frequency_divider

    @property
    def burst_pulse_left(self):
        return self._burst_pulse_left

    @property
    def qsw_adjustment_output_delay(self):
        return self._qsw_adjustment_output_delay

    @property
    def repetition_rate(self):
        return self._repetition_rate

    @property
    def synchronization_mode(self):
        return self._synchronization_mode

    @property
    def burst_length(self):
        return self._burst_length


class LLPMKU:
    def __init__(self):
        self.id = 54
        self._power = "ON"

    @property
    def power(self):
        return self._power


class MaxiOPG:
    def __init__(self):
        self.id = 31
        self._wavelength = 650
        self._configuration = "No SCU"

    @property
    def wavelength(self):
        return self._wavelength

    @property
    def configuration(self):
        return self._configuration


class MiniOPG:
    def __init__(self):
        self.id = 56
        self._error_code = 0

    @property
    def error_code(self):
        return self._error_code


class TK6:
    def __init__(self):
        self.id = 44
        self.id_2 = 45
        self._display_temperature = 45
        self._set_temperature = 45
        self._display_temperature_2 = 19
        self._set_temperature_2 = 19

    @property
    def display_temperature(self):
        return self._display_temperature

    @property
    def set_temperature(self):
        return self._set_temperature

    @property
    def display_temperature_2(self):
        return self._display_temperature_2

    @property
    def set_temperature_2(self):
        return self._set_temperature_2


class HV40W:
    def __init__(self):
        self.id = 41
        self._hv_voltage = 1.5

    @property
    def hv_voltage(self):
        return self._hv_voltage


class DelayLin:
    def __init__(self):
        self.id = 40
        self._error_code = 0

    @property
    def error_code(self):
        return self._error_code


class LDCO48BP:
    def __init__(self):
        self.id = 30
        self.id_2 = 29
        self.id_3 = 24
        self._display_temperature = 27
        self._display_temperature_2 = 25
        self._display_temperature_3 = 6

    @property
    def display_temperature(self):
        return self._display_temperature

    @property
    def display_temperature_2(self):
        return self._display_temperature_2

    @property
    def display_temperature_3(self):
        return self._display_temperature_3


class MLDCO48:
    def __init__(self):
        self.id = 33
        self.id_2 = 34
        self._display_temperature = 13
        self._display_temperature_2 = 19

    @property
    def display_temperature(self):
        return self._display_temperature

    @property
    def display_temperature_2(self):
        return self._display_temperature_2


class SimulatedTunableLaser(StateMachineDevice):
    def _initialize_data(self):
        self.interlock = "ON"
        self.cpu8000 = CPU8000()
        self.mcpu800 = MCPU800
        self.llpkmu = LLPMKU()
        self.maxiopg = MaxiOPG()
        self.miniopg = MiniOPG()
        self.tk6 = TK6()
        self.hv40w = HV40W
        self.delaylin = DelayLin()
        self.ldco48bp = LDCO48BP()
        self.mldco48 = MLDCO48()

    def _get_state_handlers(self):
        return {
            "not-propagating": State(),
            "propagating": State(),
            "interlocked": State(),
        }

    def _get_initial_state(self):
        return "not-propagating"

    def _get_transition_handlers(self):
        return OrderedDict(
            [
                (
                    ("not-propagating", "propagating"),
                    lambda: self.mcpu800.power_2 == "ON",
                ),
                (
                    ("propagating", "not-propagating"),
                    lambda: self.mcpu800.power_2 == "OFF",
                ),
                (("not-propagating", "interlocked"), lambda: self.interlock == "OFF"),
                (("propagating", "interlocked"), lambda: self.interlock == "OFF"),
            ]
        )

    @property
    def state(self):
        return self._csm.state


class TunableLaserStreamInterface(StreamInterface):
    commands = {Cmd("get_wavelength", r"^$")}

    in_terminator = "x03"
    out_terminator = "x03"
