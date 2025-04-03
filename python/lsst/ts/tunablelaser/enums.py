# This file is part of ts_tunablelaser.
#
# Developed for the Vera Rubin Observatory Telescope and Site Software.
# This product includes software developed by the LSST Project
# (https://www.lsst.org).
# See the COPYRIGHT file at the top-level directory of this distribution
# for details of code ownership.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

__all__ = ["Power", "Mode", "Output", "OpticalConfiguration", "SimulationMode"]

import enum


class SimulationMode(enum.IntEnum):
    OFF = 0
    ON = 1
    MOCK_INSTABILITY = 2


class Error(enum.IntEnum):
    pass


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
