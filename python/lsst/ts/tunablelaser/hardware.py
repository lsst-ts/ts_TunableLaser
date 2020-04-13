"""Implements classes corresponding to modules for the TunableLaser.

These classes correspond to one module inside of the TunableLaser.
Each class contains child registers that have values that can be read and
sometimes set.
Each class contains a method to publish its registers' values.

Notes
-----
These classes are based on the REMOTECONTROL.csv file provided by the vendor.

"""
__all__ = ["CPU8000", "MCPU800", "LLPMKU", "MaxiOPG", "MiniOPG", "TK6", "HV40W", "LDCO48BP", "MLDCO48",
           "DelayLin"]
import logging
from .ascii import AsciiRegister


class CPU8000:
    """A module for the laser.

    Parameters
    ----------
    port : `SerialCommander`
        Hands off serial duty to this port.
    simulation_mode : `bool`
        False for normal operation, true for simulation operation.

    Attributes
    ----------
    log : `logging.Logger`
        The log for the class.
    name : `str`
        Name of the module.
    id : `int`
        The ID of the module.
    port : `SerialCommander`
        The port that handles reading and writing to the laser
    power_register : `AsciiRegister`
        Handles the "Power" register for this module.
    display_current_register : `AsciiRegister`
        Handles the "Display current" register.
    fault_register : `AsciiRegister`
        Handles the "Fault code" register.


    """
    def __init__(self, port, simulation_mode=False):
        self.log = logging.getLogger(f"CPU8000")
        self.name = "CPU8000"
        self.id = 16
        self.port = port
        self.power_register = AsciiRegister(port=port, module_name=self.name, module_id=self.id,
                                            register_name="Power", simulation_mode=simulation_mode)
        self.display_current_register = AsciiRegister(port=port, module_name=self.name, module_id=self.id,
                                                      register_name="Display Current",
                                                      simulation_mode=simulation_mode)
        self.fault_register = AsciiRegister(port=port, module_name=self.name, module_id=self.id,
                                            register_name="Fault code", simulation_mode=simulation_mode)
        if simulation_mode:
            self.power_register.register_value = "ON"
            self.display_current_register.register_value = "1.5A"
            self.fault_register.register_value = "0h"
        self.log.debug(f"{self.name} Module initialized")

    def publish(self):
        """Publish the registers located inside of this module.

        Returns
        -------
        None

        """
        self.power_register.get_register_value()
        self.display_current_register.get_register_value()
        self.fault_register.get_register_value()

    def set_simulation_mode(self, mode):
        self.power_register.simulation_mode = mode
        self.display_current_register.simulation_mode = mode
        self.fault_register.simulation_mode = mode

    def __str__(self):
        return f"CPU8000:\n {self.power_register}\n {self.display_current_register}\n {self.fault_register}\n"


class MCPU800:
    """A hardware module for the laser.

    Parameters
    ----------
    port : `SerialCommander`
        Connects the serial port to the module.
    simulation_mode : `bool`
        False for normal operation, true for simulation operation.

    Attributes
    ----------
    name : `str`
        The name of the module.
    id : `int`
        The id of the module.
    id_2 : `int`
        The second id of the module.
    port : `SerialCommander`
        A reference to the SerialCommander object that handles the serial
        functionality.
    power_register : `AsciiRegister`
        Handles the "Power" register.
    display_current_register : `AsciiRegister`
        Handles the "Display current" register.
    fault_register : `AsciiRegister`
        Handles the "Fault code" register.
    power_register_2 : `AsciiRegister`
        Handles the "Power" register which handles the propagation.
    display_current_register_2 : `AsciiRegister`
        Handles the "Display current" register.
    fault_register_2 : `AsciiRegister`
        Handles the "Fault code" register.
    continous_burst_mode_trigger_burst_register : `AsciiRegister`
        Handles the "Continous %f Burst mode %f Trigger burst" register.
    output_energy_level_register : `AsciiRegister`
        Handles the "Output energy level" register.
    frequency_divider_register : `AsciiRegister`
        Handles the "frequency divider" register.
    burst_pulse_left_register : `AsciiRegister`
        Handles the "Burst pulse left" register.
    qsw_adjustment_output_delay_register : `AsciiRegister`
        Handles the "qsw adjustment output delay" register.
    repetition_rate_register : `AsciiRegister`
        Handles the "Repetition rate" register.
    synchronization_mode_register : `AsciiRegister`
        Handles the "Synchronization mode" register.
    burst_length_register : `AsciiRegister`
        Handles the "Burst length" register.

    """
    def __init__(self, port, simulation_mode=False):
        self.name = "M_CPU800"
        self.id = 17
        self.id_2 = 18
        self.port = port
        self.power_register = AsciiRegister(port=port, module_name=self.name, module_id=self.id,
                                            register_name="Power", simulation_mode=simulation_mode)
        self.display_current_register = AsciiRegister(port=port, module_name=self.name, module_id=self.id,
                                                      register_name="Display Current",
                                                      simulation_mode=simulation_mode)
        self.fault_register = AsciiRegister(port=port, module_name=self.name, module_id=self.id,
                                            register_name="Fault code", simulation_mode=simulation_mode)

        self.power_register_2 = AsciiRegister(port=port, module_name=self.name, module_id=self.id_2,
                                              register_name="Power", read_only=False,
                                              accepted_values=["OFF", "ON"], simulation_mode=simulation_mode)
        self.display_current_register_2 = AsciiRegister(port=port, module_name=self.name, module_id=self.id_2,
                                                        register_name="Display Current",
                                                        simulation_mode=simulation_mode)
        self.fault_register_2 = AsciiRegister(port=port, module_name=self.name, module_id=self.id_2,
                                              register_name="Fault code", simulation_mode=simulation_mode)
        self.continous_burst_mode_trigger_burst_register = AsciiRegister(
            port=port, module_name=self.name, module_id=self.id_2,
            register_name="Continuous %2F Burst mode %2F Trigger burst", read_only=False,
            accepted_values=["Continous", "Burst", "Trigger"], simulation_mode=simulation_mode)
        self.output_energy_level_register = AsciiRegister(port=port, module_name=self.name,
                                                          module_id=self.id_2,
                                                          register_name="Output Energy level",
                                                          read_only=False,
                                                          accepted_values=["OFF", "Adjust", "MAX"],
                                                          simulation_mode=simulation_mode)
        self.frequency_divider_register = AsciiRegister(port=port, module_name=self.name, module_id=self.id_2,
                                                        register_name="Frequency divider", read_only=False,
                                                        accepted_values=range(1, 5001),
                                                        simulation_mode=simulation_mode)
        self.burst_pulse_left_register = AsciiRegister(port=port, module_name=self.name, module_id=self.id_2,
                                                       register_name="Burst pulses to go",
                                                       simulation_mode=simulation_mode)
        self.qsw_adjustment_output_delay_register = AsciiRegister(port=port, module_name=self.name,
                                                                  module_id=self.id_2,
                                                                  register_name="QSW Adjustment output delay",
                                                                  simulation_mode=simulation_mode)
        self.repetition_rate_register = AsciiRegister(port=port, module_name=self.name, module_id=self.id_2,
                                                      register_name="Repetition rate",
                                                      simulation_mode=simulation_mode)
        self.synchronization_mode_register = AsciiRegister(
            port=port, module_name=self.name, module_id=self.id_2, register_name="Synchronization mode",
            simulation_mode=simulation_mode)
        self.burst_length_register = AsciiRegister(port=port, module_name=self.name, module_id=self.id_2,
                                                   register_name="Burst length", read_only=False,
                                                   accepted_values=range(1, 50001),
                                                   simulation_mode=simulation_mode)
        if simulation_mode:
            self.power_register.register_value = "ON"
            self.display_current_register.register_value = "1.3A"
            self.fault_register.register_value = "0h"

    def start_propagating(self):
        """Start the propagation of the laser.

        Returns
        -------
        None

        """
        self.power_register_2.set_register_value("ON")

    def stop_propagating(self):
        """Stop the propagation of the laser

        Returns
        -------
        None

        """
        self.power_register_2.set_register_value("OFF")

    def set_output_energy_level(self, value):
        """Set the output energy level for the laser.

        Parameters
        ----------
        value: `str`, {OFF,Adjust,MAX}

        Returns
        -------
        None
        """
        self.output_energy_level_register.set_register_value(value)

    def publish(self):
        """Publish the register values of the module.

        Returns
        -------
        None

        """
        self.power_register.get_register_value()
        self.display_current_register.get_register_value()
        self.fault_register.get_register_value()
        self.power_register_2.get_register_value()
        self.display_current_register_2.get_register_value()
        self.fault_register_2.get_register_value()
        self.continous_burst_mode_trigger_burst_register.get_register_value()
        self.output_energy_level_register.get_register_value()
        self.frequency_divider_register.get_register_value()
        self.burst_pulse_left_register.get_register_value()
        self.qsw_adjustment_output_delay_register.get_register_value()
        self.repetition_rate_register.get_register_value()
        self.synchronization_mode_register.get_register_value()
        self.burst_length_register.get_register_value()

    def set_simulation_mode(self, mode):
        self.power_register.simulation_mode = mode
        self.display_current_register.simulation_mode = mode
        self.fault_register.simulation_mode = mode
        self.power_register_2.simulation_mode = mode
        self.display_current_register_2.simulation_mode = mode
        self.fault_register_2.simulation_mode = mode
        self.continous_burst_mode_trigger_burst_register.simulation_mode = mode
        self.output_energy_level_register.simulation_mode = mode
        self.frequency_divider_register.simulation_mode = mode
        self.burst_pulse_left_register.simulation_mode = mode
        self.qsw_adjustment_output_delay_register.simulation_mode = mode
        self.repetition_rate_register.simulation_mode = mode
        self.synchronization_mode_register.simulation_mode = mode
        self.burst_length_register.simulation_mode = mode

    def __str__(self):
        return (f"M_CPU800:\n {self.power_register}\n {self.display_current_register}\n"
                f"{self.fault_register}\n {self.power_register_2}\n {self.display_current_register_2}\n"
                f"{self.fault_register_2}\n {self.continous_burst_mode_trigger_burst_register}\n"
                f"{self.output_energy_level_register}\n {self.frequency_divider_register}\n"
                f"{self.burst_pulse_left_register}\n {self.qsw_adjustment_output_delay_register}\n"
                f"{self.repetition_rate_register}\n {self.synchronization_mode_register}\n"
                f"{self.burst_length_register}\n")


class LLPMKU:
    """A hardware module for the laser.

    Parameters
    ----------
    port : `SerialCommander`
        A reference to the serial port
    simulation_mode : `bool`
        False for normal operation, true for simulation operation.

    Attributes
    ----------
    name : `str`
        The name of the module.
    id : `int`
        The id of the module.
    port : `SerialCommander`
        A reference to the serial port.
    power_register : `AsciiRegister`
        Handles the "Power" register.

    """
    def __init__(self, port, simulation_mode=False):
        self.name = "11PMKu"
        self.id = 54
        self.port = port
        self.power_register = AsciiRegister(port=port, module_name=self.name, module_id=self.id,
                                            register_name="Power", simulation_mode=simulation_mode)

    def publish(self):
        """Publish the register values of the module.

        Returns
        -------
        None

        """
        self.power_register.get_register_value()

    def set_simulation_mode(self, mode):
        self.power_register.simulation_mode = mode

    def __str__(self):
        return f"11PMKu:\n {self.power_register}"


class MaxiOPG:
    """A hardware module for the laser.

    Parameters
    ----------
    port : `SerialCommander`
        A reference to the serial port.
    simulation_mode : `bool`
        False for normal operation, true for simulation operation.

    Attributes
    ----------
    name : `str`
        The name of the module.
    id : `int`
        The id of the module.
    port : `SerialCommander`
        The reference to the serial port.
    wavelength_register : `AsciiRegister`
        Handles the "WaveLength" register.
    configuration_register : `AsciiRegister`
        Handles the "Configuration" register.
    """
    def __init__(self, port, simulation_mode=False):
        self.name = "MaxiOPG"
        self.id = 31
        self.port = port
        self.configuration = "No SCU"
        self.wavelength_register = AsciiRegister(port=port, module_name=self.name, module_id=self.id,
                                                 register_name="WaveLength", read_only=False,
                                                 accepted_values=range(300, 1100),
                                                 simulation_mode=simulation_mode)
        if self.configuration == "No SCU":
            self.configuration_register = AsciiRegister(port=port, module_name=self.name, module_id=self.id,
                                                        register_name="Configuration", read_only=False,
                                                        accepted_values=["No SCU", "F1 No SCU", "F2 No SCU"],
                                                        simulation_mode=simulation_mode)
        elif self.configuration == "SCU":
            self.configuration_register = AsciiRegister(port=port, module_name=self.name, module_id=self.id,
                                                        register_name="Configuration", read_only=False,
                                                        accepted_values=["SCU", "F1 SCU", "F2 SCU"],
                                                        simulation_mode=simulation_mode)
        else:
            raise ValueError("Invalid configuration value")

    def change_wavelength(self, wavelength):
        """Change the wavelength of the laser.

        Parameters
        ----------
        wavelength : `float`

        Returns
        -------
        None

        """
        self.wavelength_register.set_register_value(wavelength)

    def set_configuration(self, configuration):
        """Set the configuration of the output of the laser

        Parameters
        ----------
        configuration : `str`, {Det,No SCU,SCU,F1 SCU,F2 SCU,F1 No SCU,
        F2 No SCU}
            These are the output points that can be chosen.
            Note that if SCU/No SCU is set in the controller, then only those
            options with the term can be chosen.

        Returns
        -------
        None

        """
        if self.optical_alignment == "straight-through":
            self.configuration_register.set_register_value(self.configuration)
        else:
            self.configuration_register.set_register_value(f"{self.optical_alignment} {self.configuration}")

    def publish(self):
        """Publish the register values of the modules.

        Returns
        -------
        None

        """
        self.wavelength_register.get_register_value()
        self.configuration_register.get_register_value()

    def set_simulation_mode(self, mode):
        self.wavelength_register.simulation_mode = mode
        if mode:
            self.wavelength_register.register_value = 425
        self.configuration_register.simulation_mode = mode

    def __str__(self):
        return f"{self.name}:\n {self.wavelength_register}\n {self.configuration_register}\n"


class MiniOPG:
    """A hardware module for the laser.

    Parameters
    ----------
    port : `SerialCommander`
        A reference to the serial port.
    simulation_mode : `bool`
        False for normal operation, true for simulation operation.
    Attributes
    ----------
    name : `str`
        The name of the module.
    id : `int`
        The id of the module.
    port : `SerialCommander`
        A reference to the serial port.
    error_code_register : `AsciiRegister`
        Corresponds to the "Error code" register.

    """
    def __init__(self, port, simulation_mode=False):
        self.name = "MiniOPG"
        self.id = 56
        self.port = port
        self.error_code_register = AsciiRegister(port=port, module_name=self.name, module_id=self.id,
                                                 register_name="Error Code", simulation_mode=simulation_mode)

    def publish(self):
        """Publish the register values of the module.

        Returns
        -------
        None

        """
        self.error_code_register.get_register_value()

    def set_simulation_mode(self, mode):
        self.error_code_register.simulation_mode = mode

    def __str__(self):
        return f"{self.name}:\n {self.error_code_register}\n"


class TK6:
    """A hardware module for the laser.

    Parameters
    ----------
    port : `SerialCommander`
        A reference to the serial port.
    simulation_mode : `bool`
        False for normal operation, true for simulation operation.

    Attributes
    ----------
    name : `str`
        The name of the module.
    id : `int`
        The id of the module.
    id_2 : `int`
        The second id of the module.
    port : `SerialCommander`
        A reference to the serial port.
    display_temperature_register : `AsciiRegister`
        Handles the "Display temperature" register.
    set_temperature_register : `AsciiRegister`
        Handles the "Set temperature" register.
    display_temperature_register_2 : `AsciiRegister`
        Handles the "Display temperature" register.
    set_temperature_register_2 : `AsciiRegister`
        Handles the "Set temperature" register.

    """
    def __init__(self, port, simulation_mode=False):
        self.name = "TK6"
        self.id = 44
        self.id_2 = 45
        self.port = port
        self.display_temperature_register = AsciiRegister(port=port, module_name=self.name, module_id=self.id,
                                                          register_name="Display temperature",
                                                          simulation_mode=simulation_mode)
        self.set_temperature_register = AsciiRegister(port=port, module_name=self.name, module_id=self.id,
                                                      register_name="Set temperature",
                                                      simulation_mode=simulation_mode)
        self.display_temperature_register_2 = AsciiRegister(port=port, module_name=self.name,
                                                            module_id=self.id_2,
                                                            register_name="Display temperature",
                                                            simulation_mode=simulation_mode)
        self.set_temperature_register_2 = AsciiRegister(port=port, module_name=self.name, module_id=self.id_2,
                                                        register_name="Set temperature",
                                                        simulation_mode=simulation_mode)
        if simulation_mode:
            self.display_temperature_register.register_value = "45C"
            self.display_temperature_register_2.register_value = "19C"

    def publish(self):
        """Publish the register values of the module.

        Returns
        -------
        None

        """
        self.display_temperature_register.get_register_value()
        self.set_temperature_register.get_register_value()
        self.display_temperature_register_2.get_register_value()
        self.set_temperature_register_2.get_register_value()

    def set_simulation_mode(self, mode):
        self.display_temperature_register.simulation_mode = mode
        self.set_temperature_register.simulation_mode = mode
        self.display_temperature_register_2.simulation_mode = mode
        self.set_temperature_register_2.simulation_mode = mode

    def __str__(self):
        return (f"{self.name}:\n {self.display_temperature_register}\n {self.set_temperature_register}\n"
                f"{self.display_temperature_register_2}\n {self.set_temperature_register_2}\n")


class HV40W:
    """A hardware module for the laser.

    Parameters
    ----------
    port : `SerialCommander`
        A reference to the serial port.
    simulation_mode : `bool`
        False for normal operation, true for simulation operation.

    Attributes
    ----------
    name : `str`
        The name of the module.
    id : `int`
        The id of the module.
    port : `SerialCommander`
        A reference to the serial port.
    hv_voltage_register : `AsciiRegister`
        Handles the "HV Voltage" register.

    """
    def __init__(self, port, simulation_mode=False):
        self.name = "HV40W"
        self.id = 41
        self.port = port
        self.hv_voltage_register = AsciiRegister(port=port, module_name=self.name, module_id=self.id,
                                                 register_name="HV voltage", simulation_mode=simulation_mode)

    def publish(self):
        """Publishes the register values of the module.

        Returns
        -------
        None

        """
        self.hv_voltage_register.get_register_value()

    def set_simulation_mode(self, mode):
        self.hv_voltage_register.simulation_mode = mode

    def __str__(self):
        return f"{self.name}:\n {self.hv_voltage_register}\n"


class DelayLin:
    """A hardware module for the laser.

    Parameters
    ----------
    port : `SerialCommander`
        A reference to the serial port.
    simulation_mode : `bool`
        False for normal operation, true for simulation operation.

    Attributes
    ----------
    name : `str`
        The name of the module.
    id : `int`
        The id of the module.
    port : `SerialCommander`
        A reference to the serial port.
    error_code_register : `AsciiRegister`
        Handles the "Error code" register.
    """
    def __init__(self, port, simulation_mode=False):
        self.name = "DelayLin"
        self.id = 40
        self.port = port
        self.error_code_register = AsciiRegister(port=port, module_name=self.name, module_id=self.id,
                                                 register_name="Error Code", simulation_mode=simulation_mode)

    def publish(self):
        """Publish the register values of the module.

        Returns
        -------
        None

        """
        self.error_code_register.get_register_value()

    def set_simulation_mode(self, mode):
        self.error_code_register.simulation_mode = mode

    def __str__(self):
        return f"{self.name}:\n {self.error_code_register}\n"


class LDCO48BP:
    """A hardware module for the laser.

    Parameters
    ----------
    port : `SerialCommander`
        A reference to the serial port.
    simulation_mode : `bool`
        False for normal operation, true for simulation operation.
    Attributes
    ----------
    name : `str`
        The name of the module.
    id : `int`
        The id of the module.
    id_2 : `int`
        The second id of the module.
    id_3 : `int`
        The third id of the module.
    port : `SerialCommander`
        A reference to the serial port.
    display_temperature_register : `AsciiRegister`
        Handles the "Display temperature" register.
    display_temperature_register_2 : `AsciiRegister`
        Handles the "Display temperature" register.
    display_temperature_register_3 : `AsciiRegister`
        Handles the "Display temperature" register.

    """
    def __init__(self, port, simulation_mode=False):
        self.name = "LDCO48BP"
        self.id = 30
        self.id_2 = 29
        self.id_3 = 24
        self.port = port
        self.display_temperature_register = AsciiRegister(port=port, module_name=self.name, module_id=self.id,
                                                          register_name="Display temperature",
                                                          simulation_mode=simulation_mode)
        self.display_temperature_register_2 = AsciiRegister(port=port, module_name=self.name,
                                                            module_id=self.id_2,
                                                            register_name="Display temperature",
                                                            simulation_mode=simulation_mode)
        self.display_temperature_register_3 = AsciiRegister(port=port, module_name=self.name,
                                                            module_id=self.id_3,
                                                            register_name="Display temperature",
                                                            simulation_mode=simulation_mode)
        if simulation_mode:
            self.display_temperature_register.register_value = "27C"
            self.display_temperature_register_2.register_value = "25C"
            self.display_temperature_register_3.register_value = "6C"

    def publish(self):
        """Publish the register values of the module.

        Returns
        -------
        None
        """
        self.display_temperature_register.get_register_value()
        self.display_temperature_register_2.get_register_value()
        self.display_temperature_register_3.get_register_value()

    def set_simulation_mode(self, mode):
        self.display_temperature_register.simulation_mode = mode
        self.display_temperature_register_2.simulation_mode = mode
        self.display_temperature_register_3.simulation_mode = mode

    def __str__(self):
        return (f"{self.name}:\n {self.display_temperature_register}\n"
                f"{self.display_temperature_register_2}\n {self.display_temperature_register_3}\n")


class MLDCO48:
    """A hardware module for the laser.

    Parameters
    ----------
    port : `SerialCommander`
        A reference to the serial port.
    simulation_mode : `bool`
        False for normal operation, true for simulation operation.

    Attributes
    ----------
    name : `str`
        The name of the module.
    id : `int`
        The id of the module.
    id_2 : `int`
        The second id of the module.
    port : `SerialCommander`
        A reference to the serial port.
    display_temperature_register : `AsciiRegister`
        Handles the "Display temperature" register.
    display_temperature_register_2 : `AsciiRegister`
        Handles the "Display temperature" register.
    """
    def __init__(self, port, simulation_mode=False):
        self.name = "M_LDCO48"
        self.id = 33
        self.id_2 = 34
        self.port = port
        self.display_temperature_register = AsciiRegister(port=port, module_name=self.name, module_id=self.id,
                                                          register_name="Display temperature",
                                                          simulation_mode=simulation_mode)
        self.display_temperature_register_2 = AsciiRegister(port=port, module_name=self.name,
                                                            module_id=self.id_2,
                                                            register_name="Display temperature",
                                                            simulation_mode=simulation_mode)
        if simulation_mode:
            self.display_temperature_register.register_value = "13C"
            self.display_temperature_register_2.register_value = "19C"

    def publish(self):
        """Publish the register values of the module.

        Returns
        -------
        None

        """
        self.display_temperature_register.get_register_value()
        self.display_temperature_register_2.get_register_value()

    def set_simulation_mode(self, mode):
        self.display_temperature_register.simulation_mode = mode
        self.display_temperature_register_2.simulation_mode = mode

    def __str__(self):
        return f"{self.name}:\n {self.display_temperature_register}\n {self.display_temperature_register_2}\n"
