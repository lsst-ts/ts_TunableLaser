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
import logging
import time
from collections import OrderedDict
from datetime import datetime

import numpy as np
import pigpio
import serial
from lsst.ts import tcpip

FAN_ON = 1
FAN_OFF = 0


def execute_serial_temperature_scanner():
    asyncio.run(SerialTemperatureScanner.amain(index=None))


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
        logger: logging.Logger,
        port: int | None = 1883,
        host: str | None = tcpip.DEFAULT_LOCALHOST,
        encoding: str = tcpip.DEFAULT_ENCODING,
        terminator: bytes = tcpip.DEFAULT_TERMINATOR,
        sample_wait_time: int = 5,
        serial=None,
        temperature_windows: int = 8,
    ):
        super().__init__(
            log=logger,
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
        self.fileptr = None
        if logger is None:
            logging.basicConfig(
                format="%(asctime)s %(levelname)-8s %(message)s",
                level=logging.INFO,
                datefmt="%Y-%m-%d %H:%M:%S",
            )

            logger = logging.getLogger(__name__)
            logger.propagate = True
            self.logger = logger
        else:
            self.logger = logger
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
        self.pending_messages = []
        self.port = port
        self.host = host

        # TODO remove this debug stuff
        self.header = None

        self.config()

    async def amain(self):
        self.serial_temperature_task()

    def publish_msg(self, msg):
        self.pending_messages.append(msg)
        self.read_and_dispatch()

    async def read_and_dispatch(self) -> None:
        # read any data
        # incoming_data = self.read_str()

        # deal with data

        # send data
        while len(self.pending_messages) != 0:
            self.write_str(self.pending_messages.pop() + self.terminator)

    def config(self):
        # TODO: read config .yaml instead
        PORT = "/dev/ttyUSB0"
        BAUDRATE = 19200
        FILEFOLDER = "./logs"
        FILENAME = "temp_scanner_two_sensors_cooldown"
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

        # TODO Remove eventually, this is for debug
        # start debug csv
        date = str(datetime.now().date())
        self.fileptr = "{}/{}_{}.csv".format(FILEFOLDER, FILENAME, date)
        self.header = np.hstack([["Time"], list(self.sensor_dict.values())])
        try:
            with open(self.fileptr, "w") as file:
                file.write(",".join(self.header))
                file.write("\n")
                file.close()
        except Exception as e:
            self.logger.exception(f"Got exception when opening csv file: {e}")
            self.publish_msg(f"TS: Exception when opening csv: {e}")
            raise Exception(e)
        self.configured = True

    def set_fan(self, setting):
        if not self.configured or not self.pi.connected:
            self.publish_msg("TS: Error: Not configured properly before actuating fan")
            raise ValueError("Not configured properly before actuating fan")
        self.pi.write(self.fan_gpio, setting)

    def set_fan_on(self):
        self.set_fan(FAN_ON)

    def set_fan_off(self):
        self.set_fan(FAN_OFF)

    def handle_data(self, new_data):
        # Get New Date
        new_date = {"Time": str(datetime.now())}

        # We only care about one sensor's reading for operating the fan
        try:
            new_data[self.fan_sensor] = float(new_data[self.fan_sensor])
        except Exception as e:
            self.publish_msg(
                f"TS: Exception trying to convert data to int... Data: {new_data[self.fan_sensor], {str(e)}}"
            )
            self.logger.exception(
                f"Exception trying to convert data to int... Data: {new_data[self.fan_sensor], {str(e)}}"
            )
            return
        if new_data[self.fan_sensor] >= self.fan_turn_on_temp:
            self.logger.info(
                f"Turning ON fan, temperature: {new_data[self.fan_sensor]}"
            )
            self.set_fan_on()
        elif new_data[self.fan_sensor] < self.fan_turn_off_temp:
            self.logger.info(
                f"Turning OFF fan, temperature: {new_data[self.fan_sensor]}"
            )
            self.set_fan_off()

        # Now for telemetry, do a rolling average of all 8 sensors
        new_temperature = 0
        for reading in new_data:
            data = float(new_data[reading])
            self.logger.info(f"reading: {data}")
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
        self.logger.info(f"New rolling temperature data logged: {new_temperature}")
        self.publish_msg(f"TS: New: {new_temperature}, time: {new_date['Time']}")
        self.rolling_temperature[0] = new_temperature
        self.logger.info("test after rolling temp")

        # TODO remove this eventually, using it for debugging
        # Write to file
        try:
            with open(self.fileptr, "a") as file:  # add to file
                for key in self.header:
                    if key == "Time":
                        file.write(str(new_date["Time"]))
                    else:
                        file.write(str(new_data[key]))
                    file.write(",")
                file.write("\n")
                file.close()
        except Exception as e:
            self.publish_msg(f"TS: Exception while writing to csv: {e}")
            self.logger.exception(f"Exception while writing to csv: {e}")
            raise Exception(e)
        self.pending_messages = []

        # TODO remove this debug stuff
        self.header = None

        self.config()

    def get_data(self):
        try:
            readings = (
                self.serial.read(self.serial.inWaiting()).decode("ISO-8859-1").rstrip()
            )
            # reads all data since last read
            latest_reading = readings.split("\n")[-2]
            # Reason for taking second to last reading rather
            # than most recent is because most recent reading
            # often doesn't have values from all sensors.
            for reading in latest_reading.split(","):
                sensor_location, sensor_reading = reading.split("=")
                try:  # Not all inputs will be used
                    self.latest_data[self.sensor_dict[sensor_location]] = sensor_reading
                    self.logger.info(
                        f"New data logged, reading: {sensor_reading}, location: {sensor_location}"
                    )
                except Exception:
                    pass
        except Exception as e:
            self.publish_msg(
                f"TS: Exception: Serial Temperature Scanner tried to get data, got exception instead: {e}"
            )
            self.logger.warning(
                f"Serial Temperature Scanner tried to get data, got exception instead: {e}"
            )

    def serial_temperature_task(self):
        # Read sensors, write to file, close file,
        # waiting for WAIT_TIME between readings
        while True:
            try:
                # Get fresh data
                self.get_data()

                # Handle the data
                self.handle_data(self.latest_data)
            except Exception as e:
                self.publish_msg(f"TS: Exception: Main task excepted {e}")
                self.logger.warning(f"Main task excepted {e}")
                print(e)
            self.logger.info(f"Waiting {self.sample_wait_time} seconds")
            time.sleep(self.sample_wait_time)


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger = logging.getLogger(__name__)
    logger.propagate = True
    serial_temp_scanner = SerialTemperatureScanner(sample_wait_time=5, logger=logger)
    serial_temp_scanner.serial_temperature_task()
