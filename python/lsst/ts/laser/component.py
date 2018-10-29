import csv
import serial
from types import SimpleNamespace
from time import sleep


class LaserComponent:
    """The class that implements the TunableLaser component

    Parameters
    ----------
    port: str
        The name of the port that the laser connection is located

    Notes
    -----
    Class uses SimpleNamespace to implement laser modules into a neat python api. Each function is implemented as a
    private function which are defined after the init function.


    """
    def __init__(self,port):
        self.serial = serial.Serial(port=port or None, baudrate=19200, timeout=5)
        self.CPU8000 = SimpleNamespace(name="CPU8000",id=16,power=None, current=None,
                                       read_power=self._read_cpu8000_power,read_current=self._read_cpu8000_current)
        self.M_CPU800 = SimpleNamespace(
            name="M_CPU800",id=[17,18],power=None,propagate_state=None,fault=None,current=None,configuration=None,energy=None,
            frequency_divider=None, burst_pulse_left=None, qsw_adjustment_output_delay=None, repetition_rate=None,
            synchronization_mode=None, burst_length=None, read_power=self._read_m_cpu800_power, read_propagate=self._read_m_cpu800_power_2,
            set_propagate = self._set_m_cpu800_power_2, read_fault=self._read_m_cpu800_fault,
            read_current=self._read_m_cpu800_current, read_configuration=self._read_m_cpu800_configuration,
            set_configuration=self._set_m_cpu800_configuration, read_energy=self._read_m_cpu800_energy,
            read_frequency_divider=self._read_m_cpu800_frequency_divider,
            set_frequency_divider=self._set_m_cpu800_frequency_divider,
            read_burst_pulse_left=self._read_m_cpu800_burst_pulse_left,
            read_qsw_adjustment_output_delay=self._read_m_cpu800_qsw_adjustment_output_delay,
            read_repetition_rate=self._read_m_cpu800_repetition_rate,
            read_synchronization_mode=self._read_m_cpu800_synchronization_mode)
        self.llPMKu = SimpleNamespace(name="11PMKu", id=54, power=None, read_power=self._read_11pmku_power)
        self.MaxiOPG = SimpleNamespace(
            name="MaxiOPG", id=31, wavelength=None, configuration=None, read_wavelength=self._read_maxiopg_wavelength,
            set_wavelength=self._set_maxiopg_wavelength, read_configuration=self._read_maxiopg_configuration,
            set_configuration=self._set_maxiopg_wavelength)
        self.TK6 = SimpleNamespace(
            name="TK6", id=44, temperature=None, set_temperature=None,
            read_temperature=self._read_tk6_display_temperature, read_set_temperature=self._read_tk6_set_temperature,
            set_set_temperature=self._set_tk6_set_temperature)
        self.HV40W = SimpleNamespace(name="HV40W", id=41,hv_voltage=None, read_hv_voltage=self._read_hv40w_hv_voltage)
        self.DelayLin = SimpleNamespace(
            name="DelayLin", id=40, error_code=None, read_error_code=self._read_delaylin_error_code)
        self.MiniOPG = SimpleNamespace(
            name="MiniOPG",id=56, error_code=None, read_error_code=self._read_miniopg_error_code)
        self.LDCO48BP = SimpleNamespace(
            name="LDCO48BP", id=30, temperature=None, read_temperature=self._read_ldco48bp_display_temperature)
        self.M_LDCO48 = SimpleNamespace(
            name="M_LDCO48", id=33, temperature=None, read_temperature=self._read_m_ldco48_display_temperature)
        self._register_dictionary = {
            "Power": "power","Fault source":"fault", "Display Current": "current", "Continuous %2F Burst mode %2F Trigger burst": "configuration",
            "Output Energy level": "energy", "Frequency divider": "frequency_divider",
            "Burst pulses to go": "burst_pulse_left", "QSW Adjustment output delay": "qsw_adjustment_output_delay",
            "Repetition rate": "repetition_rate", "Synchronization mode": "synchronization_mode",
            "Burst length": "burst_mode", "WaveLength": "wavelength", "Configuration": "configuration",
            "Display temperature": "temperature", "Set temperature": "set_temperature", "HV voltage": "hv_voltage",
            "Error Code": "error_code"}

    def _read_module_register(self, name, module_id, register):
        self.serial.write(b"/{}/{}/{}\r".decode('ascii').format(name, module_id, register).encode('ascii'))
        reply = self.serial.read_until(b"\x03")
        reply = self._check_errors(reply)
        reply = self._parse_reply(reply)
        if module_id == 18 and register == "Power":
            setattr(getattr(self, name), "{}".format("propagate_state"), reply)
        elif name=="11PMKu":
            setattr(getattr(self,'llPMKu'),register, reply)
        else:
            setattr(getattr(self, name), "{}".format(self._register_dictionary[register]), reply)


    def _read_cpu8000_power(self):
        self._read_module_register(self.CPU8000.name, self.CPU8000.id, "Power")

    def _read_cpu8000_current(self):
        self._read_module_register(self.CPU8000.name, self.CPU8000.id, "Display Current")

    def _read_m_cpu800_power(self):
        self._read_module_register(self.M_CPU800.name,self.M_CPU800.id[0],"Power")

    def _read_m_cpu800_power_2(self):
        self._read_module_register(self.M_CPU800.name, self.M_CPU800.id[1], "Power")

    def _set_m_cpu800_power_2(self, state):
        if state.upper() in ["OFF", "ON"]:
            self.serial.write(b"/{}/{}/{}/{}\r".decode('ascii').format(self.M_CPU800.name,self.M_CPU800.id[1], "Power",state).encode('ascii'))
            reply = self.serial.read_until(b"\x03")
            reply = self._check_errors(reply)
        else:
            raise ValueError("Value not in accepted values list")

    def _read_m_cpu800_fault(self):
        self._read_module_register(self.M_CPU800.name, self.M_CPU800.id[0], "Fault source")

    def _read_m_cpu800_current(self):
        self._read_module_register(self.M_CPU800.name,self.M_CPU800.id[0],"Display Current")

    def _read_m_cpu800_configuration(self):
        self._read_module_register(self.M_CPU800.name,self.M_CPU800.id[1], "Continuous %2F Burst mode %2F Trigger burst")

    def _set_m_cpu800_configuration(self,configuration):
        if configuration in ['Continuous','Burst Mode', 'Trigger Burst']:
            self.serial.write(b"/{0}/{1}/{2}/{3}\r".decode('ascii').format(self.M_CPU800.name, self.M_CPU800.id[1],
                                                "Continuous %2F Burst mode %2F Trigger burst", configuration).encode('ascii'))
            reply = self.serial.read_until(b"\x03")
            reply = self._check_errors(reply)
        else:
            raise ValueError("Value not in accepted values list")

    def _read_m_cpu800_energy(self):
        self._read_module_register(self.M_CPU800.name,self.M_CPU800.id[1],"Output Energy level")

    def _read_m_cpu800_frequency_divider(self):
        self._read_module_register(self.M_CPU800.name, self.M_CPU800.id[1], "Frequency divider")

    def _set_m_cpu800_frequency_divider(self, frequency_divider):
        if int(frequency_divider) in range(1,5001):
            self.serial.write(b"/{0}/{1}/{2}/{3}\r".decode('ascii').format(
                self.M_CPU800.name, self.M_CPU800.id[1], "Frequency Divider", frequency_divider).encode('ascii'))
            reply = self.serial.read_until(b"\x03")
            reply = self._check_errors(reply)
        else:
            raise ValueError("argument not in accepted values range")

    def _read_m_cpu800_burst_pulse_left(self):
        self._read_module_register(self.M_CPU800.name, self.M_CPU800.id[1], "Burst pulses to go")

    def _read_m_cpu800_qsw_adjustment_output_delay(self):
        self._read_module_register(self.M_CPU800.name, self.M_CPU800.id[1], "QSW Adjustment output delay")

    def _read_m_cpu800_repetition_rate(self):
        self._read_module_register(self.M_CPU800.name, self.M_CPU800.id[1], "Repetition rate")

    def _read_m_cpu800_synchronization_mode(self):
        self._read_module_register(self.M_CPU800.name, self.M_CPU800.id[1], "Synchronization mode")

    def _read_m_cpu800_burst_mode(self):
        self._read_module_register(self.M_CPU800.name, self.M_CPU800.id[1], "Burst length")

    def _read_11pmku_power(self):
        self._read_module_register(self.llPMKu.name, self.llPMKu.id, "Power")

    def _read_maxiopg_wavelength(self):
        self._read_module_register(self.MaxiOPG.name, self.MaxiOPG.id, "WaveLength")

    def _set_maxiopg_wavelength(self, wavelength):
        if wavelength in range(300, 1100):
            self.serial.write(b"/{0}/{1}/{2}/{3}\r".decode('ascii').format(self.MaxiOPG.name, self.MaxiOPG.id,
                                                                           "WaveLength", wavelength).encode('ascii'))
            reply = self.serial.read_until(b"\x03")
            reply = self._check_errors(reply)
        else:
            raise ValueError("Wavelength outside of accepted range")

    def _read_maxiopg_configuration(self):
        self._read_module_register(self.MaxiOPG.name, self.MaxiOPG.id, "Configuration")

    def _set_maxiopg_configuration(self, configuration):
        if configuration in ["Det", "No SCU", "SCU", "F1 SCU", "F2 SCU", "F1 No SCU", "F2 No SCU"]:
            self.serial.write(b"/{0}/{1}/{2}/{3}\r".decode('ascii').format(self.MaxiOPG.name, self.MaxiOPG.id,
                                                                           "Configuration", configuration).
                              encode('ascii'))
        else:
            raise ValueError("Configuration not in accepted values")

    def _read_tk6_display_temperature(self):
        self._read_module_register(self.TK6.name, self.TK6.id, "Display temperature")

    def _read_tk6_set_temperature(self):
        self._read_module_register(self.TK6.name, self.TK6.id, "Set temperature")

    def _set_tk6_set_temperature(self, set_temperature):
        self.serial.write(b"/{0}/{1}/{2}/{3}\r".decode('ascii').format(self.TK6.name, self.TK6.id, "Set temperature",
                                                                       set_temperature).encode('ascii'))

    def _read_hv40w_hv_voltage(self):
        self._read_module_register(self.HV40W.name, self.HV40W.id, "HV voltage")

    def _read_delaylin_error_code(self):
        self._read_module_register(self.DelayLin.name, self.DelayLin.id, "Error Code")

    def _read_miniopg_error_code(self):
        self._read_module_register(self.MiniOPG.name, self.MiniOPG.id, "Error Code")

    def _read_ldco48bp_display_temperature(self):
        self._read_module_register(self.LDCO48BP.name, self.LDCO48BP.id, "Display temperature")

    def _read_m_ldco48_display_temperature(self):
        self._read_module_register(self.M_LDCO48.name, self.M_LDCO48.id, "Display temperature")

    def _check_errors(self, reply):
        if reply.decode('ascii').startswith("'''"):
            raise Exception(reply.decode('ascii'))
        else:
            return reply

    def _parse_reply(self, reply):
        reply = reply.decode('ascii').strip('\r\n\x03')
        return reply


def main():
    lc = LaserComponent("/dev/ttyACM0")
    lc.CPU8000.read_power()
    lc.CPU8000.read_current()
    lc.M_CPU800.read_power()
    lc.M_CPU800.read_propagate()
    # lc.M_CPU800.read_fault()
    lc.M_CPU800.read_current()
    lc.M_CPU800.read_configuration()
    lc.M_CPU800.read_energy()
    lc.M_CPU800.read_frequency_divider()
    lc.M_CPU800.read_burst_pulse_left()
    lc.M_CPU800.read_qsw_adjustment_output_delay()
    lc.M_CPU800.read_repetition_rate()
    lc.M_CPU800.read_synchronization_mode()
    lc.llPMKu.read_power()
    lc.MaxiOPG.read_wavelength()
    lc.MaxiOPG.read_configuration()
    lc.TK6.read_temperature()
    lc.TK6.read_set_temperature()
    # lc.HV40W.read_hv_voltage()
    lc.DelayLin.read_error_code()
    lc.MiniOPG.read_error_code()
    lc.LDCO48BP.read_temperature()
    lc.M_LDCO48.read_temperature()

    print(lc.CPU8000.power)
    print(lc.CPU8000.current)
    print(lc.M_CPU800.power)
    print(lc.M_CPU800.propagate_state)
    print(lc.M_CPU800.current)
    print(lc.M_CPU800.configuration)
    print(lc.M_CPU800.energy)
    print(lc.M_CPU800.frequency_divider)
    print(lc.M_CPU800.burst_pulse_left)
    print(lc.M_CPU800.qsw_adjustment_output_delay)
    print(lc.M_CPU800.repetition_rate)
    print(lc.M_CPU800.synchronization_mode)
    print(lc.llPMKu.power)
    print(lc.MaxiOPG.wavelength)
    print(lc.MaxiOPG.configuration)
    print(lc.TK6.temperature)
    print(lc.TK6.set_temperature)
    print(lc.HV40W.hv_voltage)
    print(lc.DelayLin.error_code)
    print(lc.MiniOPG.error_code)
    print(lc.LDCO48BP.temperature)
    print(lc.M_LDCO48.temperature)

    # lc.MaxiOPG.set_wavelength(550)
    # lc.MaxiOPG.set_wavelength(625)
    # lc.MaxiOPG.read_wavelength()
    # print(lc.MaxiOPG.wavelength)
    # lc.M_CPU800.set_propagate("ON")
    # lc.M_CPU800.read_propagate()
    # print(lc.M_CPU800.propagate_state)
    # lc.M_CPU800.read_fault()
    # print(lc.M_CPU800.fault)



if __name__ == '__main__':
    main()