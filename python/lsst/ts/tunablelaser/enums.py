__all__ = ["Power", "Mode", "Output"]

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
