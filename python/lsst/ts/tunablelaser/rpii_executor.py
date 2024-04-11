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

import asyncio
import logging

import laser_alignment_listener
import read_serial_temp_scanner
from lsst.ts import tcpip


def execute_laser_alignment_listener():
    """Run the laser alignment task"""
    asyncio.run(RpiiExecutor.amain(index=None))


class RpiiExecutor(tcpip.OneClientServer):
    """This is the class that implements the laser alignment script.

    Parameters
    ----------
    log : `logging.Logger`
        logger object
    port : `int`, optional
        port that the server will be hosted on, default 1883
    host : `str`, optional
        IP the server will be hosted on, default tcpip.DEFAULT_LOCALHOST
    encoding : `str`, optional
        Encoding used for the packets
    """

    def __init__(
        self,
        log: logging.Logger | None = None,
        port: int | None = 1885,
        host: str | None = tcpip.DEFAULT_LOCALHOST,
        encoding: str = tcpip.DEFAULT_ENCODING,
        terminator: bytes = tcpip.DEFAULT_TERMINATOR,
    ):
        super().__init__(
            log=log,
            host=host,
            port=port,
            connect_callback=None,
            monitor_connection_interval=0,
            name="",
            encoding=encoding,
            terminator=terminator,
        )
        self.unreported_exceptions = []
        self.script_list = [laser_alignment_listener, read_serial_temp_scanner]

    async def amain(self):
        await self.execute_all_scripts()

    # thread function that runs function in while 1 loop and reports exceptions
    async def execute_script_indefinitely(self, script):
        while True:
            try:
                return await script()
            except Exception as e:
                self.unreported_exceptions.append(
                    f"Script: {str(script)} excepted: {e}"
                )
                asyncio.sleep(30)

    # kicks off all scripts, then reports any exceptions
    async def execute_all_scripts(self):
        for script in self.script_list:
            asyncio.create_task(self.execute_script_indefinitely(script))
        while True:
            # sleep and check for exceptions
            asyncio.sleep(30)
            while len(self.unreported_exceptions) != 0:
                await self.write_str(self.unreported_exceptions.pop() + self.terminator)
