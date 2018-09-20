import csv
import serial
from types import SimpleNamespace


class LaserComponent:
    def __init__(self,port):
        self.serial = serial.Serial(port=port or None, baudrate=19200)
        self.CPU8000 = SimpleNamespace(name="CPU8000",id=16,power=None, current=None,
                                       read_power=self._read_cpu8000_power,read_current=self._read_cpu8000_current)
        self.M_CPU800 = SimpleNamespace(
            name="M_CPU800",id=17,power=None,current=None,configuration=None,energy=None,
            frequency_divider=None, burst_pulse_left=None, qsw_adjustment_output_delay=None, repetition_rate=None,
             syncronization_mode=None, burst_length=None, read_power=self._read_m_cpu800_power,
            read_current=self._read_m_cpu800_current, read_configuration=self._read_m_cpu800_configuration,
            set_configuration=self._set_m_cpu800_configuration, read_energy=self._read_m_cpu800_energy,
            read_frequency_divider=self._read_m_cpu800_frequency_divider,
            set_frequency_divider=self._set_m_cpu800_frequency_divider,
            read_burst_pulse_length=self._read_m_cpu800_burst_pulse_left,
            read_qsw_adjustment_output_delay=self._read_m_cpu800_qsw_adjustment_output_delay,
            read_repetition_rate=self._read_m_cpu800_repetition_rate,
            read_synchronization_mode=self._read_m_cpu800_synchronization_mode)
        self.llPKMu = SimpleNamespace(name="11PKMu", id=54, power=None, read_power=self._read_11pkmu_power)
        self.MaxiOPG = SimpleNamespace(
            name="MaxiOPG", id=31, wavelength=None, configuration=None, read_wavelength=self._read_maxiopg_wavelength(),
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

    def _read_cpu8000_power(self):
        self.serial.write(b"/{0}/{1}/{2}\r".decode('ascii').format(self.CPU8000.name,self.CPU8000.id, "Power").encode('ascii'))
        reply = self.serial.read_until(b"\x03")
        reply = self._check_errors(reply)
        self.CPU8000.power = reply

    def _read_cpu8000_current(self):
        self.serial.write(b"/{0}/{1}/{2}\r".decode('ascii').format(self.CPU8000.name,self.CPU8000.id, "Display Current").encode('ascii'))
        reply = self.serial.read_until(b"\x03")
        reply = self._check_errors(reply)
        self.CPU8000.current = reply

    def _read_m_cpu800_power(self):
        self.serial.write(b"/{0}/{1}/{2}\r".decode('ascii').format(self.M_CPU800.name,self.M_CPU800.id,"Power").encode('ascii'))
        reply = self.serial.read_until(b"\x03")
        reply = self._check_errors(reply)
        self.M_CPU800.power = reply

    def _read_m_cpu800_current(self):
        self.serial.write(b"/{0}/{1}/{2}\r".decode('ascii').format(self.M_CPU800.name,self.M_CPU800.id,"Display Current").encode('ascii'))
        reply = self.serial.read_until(b"\x03")
        reply = self._check_errors(reply)
        self.M_CPU800.current = reply

    def _read_m_cpu800_configuration(self):
        self.serial.write(b"/{0}/{1}/{2}\r".decode('ascii').format(self.M_CPU800.name,self.M_CPU800.id,
                                                "Continuous / Burst mode / Trigger burst").encode('ascii'))
        reply = self.serial.read_until(b"\x03")
        reply = self._check_errors(reply)
        self.M_CPU800.configuration = reply

    def _set_m_cpu800_configuration(self,configuration):
        if configuration in ['Continuous','Burst Mode', 'Trigger Burst']:
            self.serial.write(b"/{0}/{1}/{2}/{3}\r".decode('ascii').format(self.M_CPU800.name, self.M_CPU800.id,
                                                "Continuous / Burst mode / Trigger burst", configuration).encode('ascii'))
            reply = self.serial.read_until(b"\x03")
            reply = self._check_errors(reply)
        else:
            raise ValueError("Value not in accepted values list")
    def _read_m_cpu800_energy(self):
        self.serial.write(b"/{0}/{1}/{2}\r".decode('ascii').format(self.M_CPU800.name,self.M_CPU800.id,"Output Energy Level").encode('ascii'))
        reply = self.serial.read_until(b"\x03")
        reply = self._check_errors(reply)
        self.M_CPU800.energy = reply

    def _read_m_cpu800_frequency_divider(self):
        self.serial.write(b"/{0}/{1}/{2}\r".decode('ascii').format(self.M_CPU800.name, self.M_CPU800.id, "Frequency divider").encode('ascii'))
        reply = self.serial.read_until(b"\x03")
        reply = self._check_errors(reply)
        self.M_CPU800.frequency_divider = reply

    def _set_m_cpu800_frequency_divider(self, frequency_divider):
        if int(frequency_divider) in range(1,5001):
            self.serial.write(b"/{0}/{1}/{2}/{3}\r".decode('ascii').format(
                self.M_CPU800.name, self.M_CPU800.id, "Frequency Divider", frequency_divider).encode('ascii'))
        else:
            raise ValueError("argument not in accepted values range")

    def _read_m_cpu800_burst_pulse_left(self):
        self.serial.write(b"/{0}/{1}/{2}\r".decode('ascii').format(self.M_CPU800.name, self.M_CPU800.id, "Burst pulses to go").encode('ascii'))
        reply = self.serial.read_until(b"\x03")
        reply = self._check_errors(reply)
        self.M_CPU800.burst_pulse_left = reply

    def _read_m_cpu800_qsw_adjustment_output_delay(self):
        self.serial.write(b"/{0}/{1}/{2}\r".decode('ascii').format(self.M_CPU800.name, self.M_CPU800.id, "QSW Adjustment output delay").encode('ascii'))
        reply = self.serial.read_until(b"\x03")
        reply = self._check_errors(reply)
        self.M_CPU800.qsw_adjustment_output_delay = reply

    def _read_m_cpu800_repetition_rate(self):
        self.serial.write((b"/{0}/{1}/{2}\r".decode('ascii').format(self.M_CPU800.name, self.M_CPU800.id, "Repetition rate").encode('ascii')))
        reply = self.serial.read_until(b"\x03")
        reply = self._check_errors(reply)
        self.M_CPU800.repetition_rate = reply

    def _read_m_cpu800_synchronization_mode(self):
        self.serial.write(b"/{0}/{1}/{2}\r".decode('ascii').format(self.M_CPU800.name, self.M_CPU800.id, "Synchronization mode").encode('ascii'))
        reply = self.serial.read_until(b"\x03")
        reply = self._check_errors(reply)
        self.M_CPU800.synchronization_mode = reply

    def _read_m_cpu800_burst_mode(self):
        self.serial.write(b"/{0}/{1}/{2}\r".decode('ascii').format(self.M_CPU800.name, self.M_CPU800.id, "Burst length").encode('ascii'))
        reply = self.serial.read_until(b"\x03")
        reply = self._check_errors(reply)
        self.M_CPU800.burst_length = reply

    def _read_11pkmu_power(self):
        self.serial.write(b"/{0}/{1}/{2}\r".decode('ascii').format(self.llPKMu.name, self.llPKMu.id, "Power").encode('ascii'))
        reply = self.serial.read_until(b"\x03")
        reply = self._check_errors(reply)
        self.llPKMu.power = reply

    def _read_maxiopg_wavelength(self):
        self.serial.write(b"/{0}/{1}/{2}".decode('ascii').format(self.MaxiOPG.name, self.MaxiOPG.id, "Wavelength").encode('ascii'))
        reply = self.serial.read_until(b"\x03")
        reply = self._check_errors(reply)
        self.MaxiOPG.wavelength = reply

    def _set_maxiopg_wavelength(self, wavelength):
        if wavelength in range(250, 1000):
            self.serial.write(b"/{0}/{1}/{2}/{3}".decode('ascii').format(self.MaxiOPG.name, self.MaxiOPG.id, "Wavelength", wavelength).encode('ascii'))
        else:
            raise ValueError("Wavelength outside of accepted range")

    def _read_maxiopg_configuration(self):
        self.serial.write(b"/{0}/{1}/{2}".decode('ascii').format(self.MaxiOPG.name, self.MaxiOPG.id, "Configuration").encode('ascii'))
        reply = self.serial.read_until(b"\x03")
        reply = self._check_errors(reply)
        self.MaxiOPG.configuration = reply

    def _set_maxiopg_configuration(self, configuration):
        if configuration in ["Det", "No SCU", "SCU", "F1 SCU", "F2 SCU", "F1 No SCU", "F2 No SCU"]:
            self.serial.write(b"/{0}/{1}/{2}/{3}".decode('ascii').format(self.MaxiOPG.name, self.MaxiOPG.id, "Configuration", configuration).encode('ascii'))
        else:
            raise ValueError("Configuration not in accepted values")

    def _read_tk6_display_temperature(self):
        self.serial.write(b"/{0}/{1}/{2}\r".decode('ascii').format(self.TK6.name, self.TK6.id, "Display temperature").encode('ascii'))
        reply = self.serial.read_until(b"\x03")
        reply = self._check_errors(reply)
        self.TK6.temperature = reply

    def _read_tk6_set_temperature(self):
        self.serial.write(b"{0}/{1}/{2}".decode('ascii').format(self.TK6.name, self.TK6.id, "Set temperature").encode('ascii'))
        reply = self.serial.read_until(b"\x03")
        reply = self._check_errors(reply)
        self.TK6.set_temperature = reply

    def _set_tk6_set_temperature(self, set_temperature):
        self.serial.write(b"/{0}/{1}/{2}/{3}".decode('ascii').format(self.TK6.name, self.TK6.id, "Set temperature", set_temperature).encode('ascii'))

    def _read_hv40w_hv_voltage(self):
        self.serial.write(b"/{}/{}/{}".decode('ascii').format(self.HV40W.name, self.HV40W, "HV voltage").encode('ascii'))
        reply = self.serial.read_until(b"\x03")
        self._check_errors(reply)
        self.HV40W.voltage = reply

    def _read_delaylin_error_code(self):
        self.serial.write(b"/{}/{}/{}".decode('ascii').format(self.DelayLin.name, self.DelayLin.id, "Error Code").encode('ascii'))
        reply = self.serial.read_until(b"\x03")
        reply = self._check_errors(reply)
        self.DelayLin.error_code = reply

    def _read_miniopg_error_code(self):
        self.serial.write(b"/{}/{}/{}".decode('ascii').format(self.MiniOPG.name, self.MiniOPG.id, "Error Code").encode('ascii'))
        reply = self.serial.read_until(b"\x03")
        reply = self._check_errors(reply)
        self.MiniOPG.error_code = reply

    def _read_ldco48bp_display_temperature(self):
        self.serial.write(b"/{}/{}/{}".decode('ascii').format(self.LDCO48BP.name, self.LDCO48BP.id, "Display temperature").encode('ascii'))
        reply = self.serial.read_until(b"\x03")
        reply = self._check_errors(reply)
        self.LDCO48BP.temperature = reply

    def _read_m_ldco48_display_temperature(self):
        self.serial.write(b"/{}/{}/{}".decode('ascii').format(self.M_LDCO48.name, self.M_LDCO48.id, "Display temperature").encode('ascii'))
        reply = self.serial.read_until(b"\x03")
        reply = self._check_errors(reply)
        self.M_LDCO48.temperature = reply

    def _check_errors(self, reply):
        if reply.decode('ascii').starts_with("```"):
            raise Exception(reply.decode('ascii'))
        else:
            return reply


def main():
    lc = LaserComponent(None)

if __name__ == '__main__':
    main()