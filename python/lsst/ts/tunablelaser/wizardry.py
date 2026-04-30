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

NUMBER_OF_RETRIES: int = 10
"""Number of retries to attempt in case of communication loss."""

DEFAULT_SLEEP: float = 1
"""Amount of time to sleep by default."""

NUMBER_OF_CONNECTION_RETRIES: int = 3
"""Number of connection retries."""

SLEEP_BETWEEN_REGISTERS: float = 0.055
"""Amount of time to sleep between reading registers."""

DEFAULT_TELEMETRY_RATE: float = 1
"""Default delay between telemetry loop iterations."""

MISSING_TEMPERATURE_VALUE: float = 0
"""Placeholder telemetry value for temperature channels absent from a model."""

DEVICE_TIMEOUT_READ_RETRIES: int = 1
"""Number of retries for transient downstream device timeout responses."""

DEVICE_TIMEOUT_READ_DELAY: float = 0.1
"""Delay between downstream device timeout read retries."""

COMMAND_TIMEOUT: float = 5
"""Timeout for one ASCII command write/read transaction."""

DEFAULT_CONNECT_TIMEOUT: float = 5
"""Timeout for one TCP/IP connection attempt."""

STX_NODE_SUBADDRESS_LEN: int = 5
"""Length of the CompoWay-F STX/node/subaddress response field."""

END_CODE_LEN: int = 2
"""Length of the CompoWay-F end-code response field."""

MRC_SRC_LEN: int = 4
"""Length of the CompoWay-F MRC/SRC response field."""

RESPONSE_CODE_LENGTH: int = 4
"""Length of the CompoWay-F response-code field."""

BCC_LEN: int = 1
"""BCC length."""

DEFAULT_LASER_WARMUP_DELAY: float = 10
"""Default warmup delay after enabling laser propagation."""

SIDE_CHANNEL_CLIENT_SLEEP: float = 1
"""Delay between side-channel client read attempts."""

SIDE_CHANNEL_CLIENT_TIMEOUT: float = 10
"""Timeout for one side-channel client read."""

DEFAULT_TEMPERATURE_CTRL_PORT: int = 50000
"""Default TCP/IP port for the temperature controller."""

REAL_FCU_PORT: int = 8081
"""TCP/IP port for the real FCU service."""

MOCK_FCU_PORT: int = 17000
"""TCP/IP port for the FCU simulator."""

FCU_SERVER_START_ITERATIONS: int = 100
"""Maximum number of FCU server startup polling attempts."""

FCU_SERVER_START_SLEEP: float = 0.01
"""Delay between FCU server startup polling attempts."""

MOCK_SERVER_TERMINATOR: bytes = b"\r\n\x03"
"""Line terminator used by the mock laser servers."""

MOCK_COMPOWAY_READ_CAP: int = 64
"""Maximum bytes to scan for ETX when parsing mock CompoWay-F frames."""

MOCK_UNSTABLE_REPLY_WEIGHT: float = 0.3
"""Mock-server weight for returning a simulated timeout response."""

MOCK_STABLE_REPLY_WEIGHT: float = 0.7
"""Mock-server weight for returning a normal response when unstable."""

MOCK_STATUS_PUBLISH_INTERVAL: float = 1
"""Delay between mock side-channel status publishing checks."""
