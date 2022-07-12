__all__ = ["Power", "Mode", "Output", "SCUConfiguration", "NoSCU"]

import enum


class Power(str, enum.Enum):
    """The power states for the laser's propagation module."""

    ON = "ON"
    OFF = "OFF"
    FAULT = "FAULT"


class Mode(str, enum.Enum):
    """The different propagation modes of the laser."""

    CONTINUOUS = "Continuous"
    """The laser pulses continuously."""
    BURST = "Burst"
    """The laser pulses with a burst of energy at regular interval."""
    TRIGGER = "Trigger"
    """The laser pulses when using an external trigger."""


class Output(str, enum.Enum):
    """The output energy level."""

    OFF = "OFF"
    """The laser outputs no energy"""
    ADJUST = "Adjust"
    """A calibration energy level where the energy level adjusts."""
    MAX = "MAX"
    """Maximum energy level for the laser."""


class SCUConfiguration(str, enum.Enum):
    """The Spectral Cleaning Unit configuration"""

    SCU = "SCU"
    """Pass the beam straight-through the SCU."""
    F1_SCU = "F1 SCU"
    """Direct the beam through the F1 after passing through the SCU."""
    F2_SCU = "F2 SCU"
    """Direct the beam through the F2 after passing through the SCU."""


class NoSCU(str, enum.Enum):
    """The no Spectral Cleaning Unit configuration"""

    NO_SCU = "No SCU"
    """Pass the beam straight-through."""
    F1_NO_SCU = "F1 No SCU"
    """Pass the beam to F1 output."""
    F2_NO_SCU = "F2 No SCU"
    """Pass the beam to F2 output."""
