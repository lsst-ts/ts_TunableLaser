__all__ = ["Power", "Mode", "Output", "OpticalConfiguration"]

import enum


class Power(enum.StrEnum):
    """The power states for the laser's propagation module."""

    ON = "ON"
    OFF = "OFF"
    FAULT = "FAULT"


class Mode(enum.StrEnum):
    """The different propagation modes of the laser."""

    CONTINUOUS = "Continuous"
    """The laser pulses continuously."""
    BURST = "Burst"
    """The laser pulses with a burst of energy at regular interval."""
    TRIGGER = "Trigger"
    """The laser pulses when using an external trigger."""


class Output(enum.StrEnum):
    """The output energy level."""

    OFF = "OFF"
    """The laser outputs no energy"""
    ADJUST = "Adjust"
    """A calibration energy level where the energy level adjusts."""
    MAX = "MAX"
    """Maximum energy level for the laser."""


class OpticalConfiguration(enum.StrEnum):
    """Configuration of the optical output"""

    SCU = "SCU"
    """Pass the beam straight-through the SCU."""
    F1_SCU = "F1 SCU"
    """Direct the beam through the F1 after passing through the SCU."""
    F2_SCU = "F2 SCU"
    """Direct the beam through the F2 after passing through the SCU."""
    NO_SCU = "No SCU"
    """Pass the beam straight-through."""
    F1_NO_SCU = "F1 No SCU"
    """Pass the beam to F1 output."""
    F2_NO_SCU = "F2 No SCU"
    """Pass the beam to F2 output."""
