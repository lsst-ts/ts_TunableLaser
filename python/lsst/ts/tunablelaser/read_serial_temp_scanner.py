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

""" Script to readout temperature sensors from serial device for laser
    The script is currently setup to write to a file every time a measurement
    is made so that the file can be accessed while the script is running
"""

__all__ = ["SerialTemperatureScanner", "execute_serial_temperature_scanner"]

import asyncio
import functools
import logging
from collections import OrderedDict

import pigpio
import serial
from lsst.ts import tcpip

FAN_ON = 1
FAN_OFF = 0


def execute_serial_temperature_scanner():
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    log = logging.getLogger(__name__)
    log.propagate = True
    serial_temp_scanner = SerialTemperatureScanner(log=log)
    asyncio.run(serial_temp_scanner.amain(index=None))


class SerialTemperatureScanner(tcpip.OneClientServer):
    """This is the class that implements the Serial Temperature Scanner script.

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
    terminator: `bytes`, optional
        terminating character used for packets
    sample_wait_time: `int`, optional
        time to wait between getting temperature samples
    serial: `serial` or `None`, optional
        serial object that the temperature scanner device is connected
    temperature_windows: `int`, optional
        Amount of temperature windows to average for rolling avg window

    """

    def __init__(
        self,
        log: logging.Logger | None = None,
        port: int | None = 1884,
        host: str | None = tcpip.DEFAULT_LOCALHOST,
        encoding: str = tcpip.DEFAULT_ENCODING,
        terminator: bytes = tcpip.DEFAULT_TERMINATOR,
        sample_wait_time: int = 5,
        serial=None,
        temperature_windows: int = 8,
    ):
        self.log = log
        super().__init__(
            log=self.log,
            port=port,
            host=host,
            connect_callback=None,
            monitor_connection_interval=0,
            name="",
            encoding=encoding,
            terminator=terminator,
        )

        self.serial = serial
        self.sensor_dict = {}
        self.sample_wait_time = sample_wait_time

        # Fan sensor
        self.fan_sensor = ""
        self.fan_gpio = None
        self.fan_turn_on_temp = 0
        self.fan_turn_off_temp = 0

        self.latest_data = {sensor_name: 0 for sensor_name in self.sensor_dict}
        self.rolling_temperature = [0 for _ in range(temperature_windows)]

        self.pi = pigpio.pi()

        self.configured = False
        self.first_run = True
        self.encoding = encoding
        self.port = port
        self.host = host
        self.loop = asyncio.get_running_loop()

        self.config()

    async def amain(self):
        await self.serial_temperature_task()

    def config(self):
        # TODO: read config .yaml instead
        PORT = "/dev/ttyUSB0"
        BAUDRATE = 19200
        self.sensor_dict = OrderedDict(
            {"C01": "Ambient", "C02": "Laser", "C03": "FC"}
        )  # These will need to be in some configuration file

        # Define serial connection
        ser = serial.Serial(
            port=PORT,
            baudrate=BAUDRATE,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=1,
        )
        self.serial = ser

        # fan sensor
        self.fan_sensor = "Ambient"
        self.fan_gpio = 4
        self.fan_turn_on_temp = 25
        hysteresis = 2
        self.fan_turn_off_temp = self.fan_turn_on_temp - hysteresis

        self.configured = True

    async def set_fan(self, setting):
        if not self.configured or not self.pi.connected:
            await self.write_str(
                "TS: Error: Not configured properly before actuating fan"
            )
            raise ValueError("Not configured properly before actuating fan")
        await self.loop.run_in_executor(
            None, functools.partial(self.pi.write, self.fan_gpio, setting)
        )

    async def set_fan_on(self):
        await self.set_fan(FAN_ON)

    async def set_fan_off(self):
        await self.set_fan(FAN_OFF)

    async def handle_data(self, new_data):
        # We only care about one sensor's reading for operating the fan
        try:
            new_data[self.fan_sensor] = float(new_data[self.fan_sensor])
        except Exception as e:
            await self.write_str(
                f"TS: Exception trying to convert data to int... Data: {new_data[self.fan_sensor], {str(e)}}"
            )
            self.log.exception(
                f"Exception trying to convert data to int... Data: {new_data[self.fan_sensor], {str(e)}}"
            )
            return
        if new_data[self.fan_sensor] >= self.fan_turn_on_temp:
            self.log.info(f"Turning ON fan, temperature: {new_data[self.fan_sensor]}")
            self.set_fan_on()
        elif new_data[self.fan_sensor] < self.fan_turn_off_temp:
            self.log.info(f"Turning OFF fan, temperature: {new_data[self.fan_sensor]}")
            self.set_fan_off()

        # Now for telemetry, do a rolling average of all 8 sensors
        new_temperature = 0
        for reading in new_data:
            data = float(new_data[reading])
            self.log.info(f"reading: {data}")
            new_temperature += data
        new_temperature = new_temperature / len(new_data)

        # Handle initial data loading
        if self.first_run:
            self.first_run = False
            for i in range(len(self.rolling_temperature)):
                self.rolling_temperature[i] = new_temperature
        else:
            # Update rolling temperature windows
            # freshest data starts at 0 index and goes towards max length index
            for i in range(len(self.rolling_temperature) - 1, 0, -1):
                self.rolling_temperature[i] = self.rolling_temperature[i - 1]

        # Update freshest at index 0
        self.log.info(f"New rolling temperature data logged: {new_temperature}")
        await self.write_str(f"TS: New: {new_temperature}")
        self.rolling_temperature[0] = new_temperature
        self.log.info("test after rolling temp")

    async def get_data(self):
        try:
            in_waiting = await self.loop.run_in_executor(None, self.serial.inWaiting)
            readings = await self.loop.run_in_executor(
                None, functools(self.serial.read, in_waiting)
            )
            readings = readings.decode("ISO-8859-1").rstrip()
            readings = readings
            # reads all data since last read
            latest_reading = readings.split("\n")[-2]
            # Reason for taking second to last reading rather
            # than most recent is because most recent reading
            # often doesn't have values from all sensors.
            for reading in latest_reading.split(","):
                sensor_location, sensor_reading = reading.split("=")
                try:  # Not all inputs will be used
                    self.latest_data[self.sensor_dict[sensor_location]] = sensor_reading
                    self.log.info(
                        f"New data logged, reading: {sensor_reading}, location: {sensor_location}"
                    )
                except Exception:
                    pass
        except Exception as e:
            await self.write_str(
                f"TS: Exception: Serial Temperature Scanner tried to get data, got exception instead: {e}"
            )
            self.log.warning(
                f"Serial Temperature Scanner tried to get data, got exception instead: {e}"
            )

    async def serial_temperature_task(self):
        # Read sensors, write to file, close file,
        # waiting for WAIT_TIME between readings
        while True:
            try:
                # Get fresh data
                await self.get_data()

                # Handle the data
                await self.handle_data(self.latest_data)
            except Exception as e:
                await self.write_str(f"TS: Exception: Main task excepted {e}")
                self.log.warning(f"Main task excepted {e}")
            self.log.info(f"Waiting {self.sample_wait_time} seconds")
            await asyncio.sleep(self.sample_wait_time)
