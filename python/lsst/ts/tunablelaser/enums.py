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

__all__ = ["Power", "Mode", "Output", "OpticalConfiguration", "SimulationMode", "ErrorCode"]

import enum


class SimulationMode(enum.IntEnum):
    """The simulation mode values."""

    OFF = 0
    """Connect to real hardware."""
    ON = 1
    """Connect to simulated hardware."""
    MOCK_INSTABILITY = 2
    """Connect to simulated hardware that is network unstable."""


class ErrorCode(enum.IntEnum):
    """CSC fault codes.

    These mirror the error-code space exposed by the TunableLaser XML enum,
    but are kept local to this package so call sites do not need to depend on
    the XML-generated enum directly.
    """

    ASCII_ERROR = 7301
    """ASCII protocol or parsing error."""
    GENERAL_ERROR = 7302
    """General controller or runtime error."""
    TIMEOUT_ERROR = 7303
    """Timeout while waiting for hardware response."""
    HW_CPU_ERROR = 7304
    """Hardware fault reported by a laser CPU module."""


class Power(enum.IntEnum):
    """The power states for the laser's propagation module."""

    ON = 1
    OFF = 0
    FAULT = 2


class Mode(enum.IntEnum):
    """The different propagation modes of the laser."""

    CONTINUOUS = 0
    """The laser pulses continuously."""
    BURST = 1
    """The laser pulses with a burst of energy at regular interval."""
    TRIGGER = 2
    """The laser pulses when using an external trigger."""


class Output(enum.IntEnum):
    """The output energy level."""

    OFF = 0
    """The laser outputs no energy"""
    ADJUST = 1
    """A calibration energy level where the energy level adjusts."""
    MAX = 2
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
