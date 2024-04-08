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
from time import sleep

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
    logger : `logging.Logger`
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
        logger: logging.Logger,
        port: int | None = 1885,
        host: str | None = tcpip.DEFAULT_LOCALHOST,
        encoding: str = tcpip.DEFAULT_ENCODING,
        terminator: bytes = tcpip.DEFAULT_TERMINATOR,
    ):
        super().__init__(
            log=logger,
            host=host,
            port=port,
            connect_callback=None,
            monitor_connection_interval=0,
            name="",
            encoding=encoding,
            terminator=terminator,
        )
        self.KillAll = False
        self.UnreportedExceptions = []
        self.ScriptList = [laser_alignment_listener, read_serial_temp_scanner]

    async def amain(self):
        self.execute_all_scripts()

    # thread function that runs function in while 1 loop and reports exceptions
    async def execute_script_indefinitely(self, script):
        try:
            return await script()
        except Exception as e:
            self.UnreportedExceptions.append(f"Script: {str(script)} excepted: {e}")
            sleep(30)

    # kicks off all scripts, then reports any exceptions
    def execute_all_scripts(self):
        for script in self.ScriptList:
            asyncio.create_task(self.execute_script_indefinitely(script))
        while True:
            # sleep and check for exceptions
            sleep(30)
            while len(self.UnreportedExceptions) != 0:
                self.write_str(self.UnreportedExceptions.pop() + self.terminator)


if __name__ == "__main__":
    executor = RpiiExecutor()
    executor.execute_all_scripts()
