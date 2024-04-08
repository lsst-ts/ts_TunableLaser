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

""" This a script for the raspberry pi running alongside the TunableLaser CSC
    This script's purpose is to listen for 1kHz laser misalignment and
    activate an interlock
"""

__all__ = ["LaserAlignmentListener", "execute_laser_alignment_listener"]

import asyncio
import datetime
import logging
from time import sleep

import matplotlib.pyplot as plt
import numpy as np
import pigpio
import sounddevice as sd
from lsst.ts import tcpip
from scipy.fftpack import fft

RELAY_ON = 1
RELAY_OFF = 0


def execute_laser_alignment_listener():
    """Run the laser alignment task"""
    asyncio.run(LaserAlignmentListener.amain(index=None))


class LaserAlignmentListener(tcpip.OneClientServer):
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
    terminator: `bytes`, optional
        terminating character used for packets
    sample_record_dur: `float`, optional
        sample recording duration
    input: `int`, optional
        index of sd device input
    output: `int`, optional
        index of sd device output
    fs: `int`, optional
        sample frequency
    """

    def __init__(
        self,
        logger: logging.Logger,
        port: int | None = 1883,
        host: str | None = tcpip.DEFAULT_LOCALHOST,
        encoding: str = tcpip.DEFAULT_ENCODING,
        terminator: bytes = tcpip.DEFAULT_TERMINATOR,
        sample_record_dur: float = 0.1,
        input: int = 2,
        output: int = 4,
        fs: int | None = None,
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

        self.logger = logger
        self.relay_gpio = None
        self.configured = False
        self.fileptr = None
        self.pending_messages = []

        self.input = input
        self.output = output
        self.sample_record_dur = sample_record_dur

        sd.default.device = (input, output)
        if fs is None:
            self.fs = sd.query_devices(input)["default_samplerate"]
        else:
            self.fs = fs

        self.relay_gpio = 7
        self.configured = True
        self.pi = pigpio.pi()

    async def amain(self):
        """Script amain"""
        self.open_laser_interrupt()
        self.laser_alignment_task(self.sample_record_dur, self.fs)

    def publish_msg(self, msg):
        """Function that adds msg to be sent to pending msgs"""
        self.pending_messages.append(msg)
        self.read_and_dispatch()

    def read_and_dispatch(self):
        """Will pop off pending messages and send them"""
        # read data
        # incoming_data = self.read_str()
        # handle data

        # send data
        while len(self.pending_messages) != 0:
            self.write_str(self.pending_messages.pop() + self.terminator)

    def record_data(self, duration, fs):
        """Records sample data from sd device"""
        self.logger.debug("Check input settings")
        sd.check_input_settings(device=self.input, samplerate=fs, channels=1)
        self.logger.debug(f"Starting to record for {duration} seconds")
        data = sd.rec(
            frames=int(duration * fs), samplerate=fs, channels=1, blocking=True
        )
        return data

    def analyze_data(self, data, fs):
        """analyzes all sound data and determines if there is a problem"""
        # average the tracks
        # a = (data.T[0] + data.T[1])/2.0
        a = data.T[0]
        # Make the array an even size
        if (len(a) % 2) != 0:
            self.logger.debug(f"Length of a is {len(a)}, removing last value")
            a = a[0:-1]
            self.logger.debug(f"Length of a is now {len(a)}")

        # sample points
        N = len(a)
        # sample spacing
        T = 1.0 / fs

        yf0 = fft(a)
        # but only need half the array
        yf = yf0[: N // 2]
        xf = np.linspace(0.0, 1.0 / (2.0 * T), N // 2)

        psd = abs((2.0 / N) * yf) ** 2.0

        # Only plot in debug mode
        # if self.logger.level >= logging.DEBUG:
        #    plot_data(data, fs, xf, yf, psd)

        # check if signal is detected
        # threshold is in sigma over the range of 950-1050 Hz
        threshold = 10

        self.logger.debug(
            f"Median of frequency vals are {(np.median(xf[(xf > 995) * (xf < 1005)])):0.2f}"
        )
        psd_at_1kHz = np.max(psd[(xf > 995) * (xf < 1005)])
        bkg = np.median(psd[(xf > 950) * (xf < 1050)])

        self.logger.debug(
            f"PSD max value in frequency window of 995-1050 Hz is {(psd_at_1kHz / bkg):0.2f} sigma"
        )

        self.logger.debug(f"Median value over range from 900-1000 Hz is {bkg:0.2E}")
        condition = (psd_at_1kHz) > threshold * bkg
        if condition:
            return True
        else:
            return False

    def plot_data(self, data, fs, xf, yf, psd):
        length = data.shape[0] / fs

        plt.clf()
        time = np.linspace(0.0, length, data.shape[0])
        plt.subplot(1, 3, 1)
        plt.plot(time, data[:, 0], label="Left channel")
        plt.plot(time, data[:, 1], label="Right channel")
        plt.xlim(0, 1e-2)
        plt.xlabel("Time [s]")
        plt.ylabel("Amplitude")

        plt.subplot(1, 3, 2)
        plt.plot(xf, psd, ".-")
        plt.xlim(0, 1300)
        plt.xlabel("Frequency (Hz)")
        plt.ylabel("PSD [units TBD]")
        plt.draw()
        plt.pause(0.001)

        plt.subplot(1, 3, 3)
        plt.plot(xf, psd, ".-")
        plt.xlim(900, 1100)
        plt.xlabel("Frequency (Hz)")
        plt.ylabel("PSD [units TBD]")
        plt.draw()
        plt.pause(0.001)

    def set_relay(self, setting: int):
        if not self.configured and not self.pi.connected:
            self.publish_msg(
                "LI: Error: Not configured properly before actuating relay"
            )
            raise ValueError("Not configured properly before actuating relay")
        self.pi.write(self.relay_gpio, setting)

    def set_relay_on(self):
        self.set_relay(RELAY_ON)

    def set_relay_off(self):
        self.set_relay(RELAY_OFF)

    def open_laser_interrupt(self):
        self.set_relay_off()
        self.logger.info("Laser interrupt opened")
        self.publish_msg("LI: Opened")

    def close_laser_interrupt(self):
        self.set_relay_on()
        self.logger.info("Laser Interrupt Activated, laser propagation disabled")
        self.publish_msg("LI: Closed")

    def restart(self):
        self.logger.info("Reset button pushed")
        self.publish_msg("LI: Reset button pushed")
        self.open_laser_interrupt()

    def get_relay_status(self):
        # bits are flipped since self.relay.value returns a 0
        # when it's able to propagate
        return not self.pi.read(self.relay_gpio)

    def laser_alignment_task(self, time: float | None = None, fs: float | None = None):
        if time is None:
            time = self.sample_record_dur
        if fs is None:
            fs = self.fs
        try:
            self.logger.info("Starting monitoring task")

            FILEFOLDER = "./logs"
            FILENAME = "laser_alignment"

            # Declare how many iterations have to be
            # above the threshold to shut off the laser
            count_threshold = 7  # 10
            count = 0

            self.fileptr = "{}/{}_{}.csv".format(
                FILEFOLDER, FILENAME, str(datetime.now().date())
            )
            header = np.hstack([["Time"], ["fs"], ["Result"]])
            with open(self.fileptr, "w") as file:
                file.write(",".join(header))
                file.write("\n")
                file.close()

            # Loop forever
            while True:
                if self.get_relay_status() is True:
                    data = self.record_data(time, fs)
                    result = self.analyze_data(data, fs)

                    if result and count > count_threshold - 1:
                        self.logger.warning(
                            "Detected misalignment in audible safety circuit"
                        )
                        self.close_laser_interrupt()
                        self.logger.warning("Interlock sleeping for 10 seconds...")
                        time.sleep(10)
                        self.logger.warning("Interlock re-opening now...")
                        self.open_laser_interrupt()
                        count = 0
                    elif result:
                        self.logger.info(
                            f"Experienced value above threshold {count+1} times"
                        )
                        count += 1
                    else:
                        count = 0

                    # TODO remove debug csv
                    with open(self.fileptr, "w") as file:
                        file.write(
                            ",".join(datetime.time().now(), str(fs), str(result))
                        )
                        file.write("\n")
                        file.close()
                else:
                    self.logger.info(f"Sleeping for {1} seconds.")
                    sleep(1)
        except Exception as e:
            self.publish_msg(f"LI: Exception: Main task excepted: {e}")
            self.logger.exception(f"Main task excepted: {e}")


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger = logging.getLogger(__name__)
    logger.propagate = True

    logger.debug(f"Available devices are: {sd.query_devices()}")

    laser_task = LaserAlignmentListener(logger=logger)

    input = 2
    output = 4
    # sd.default.device = (1, 2)
    # 2 works for output with IC94 sound setup input never worked
    sd.default.device = (input, output)

    # print(sd.query_devices(input))
    fs = sd.query_devices(input)["default_samplerate"]
    # time sampling
    time = 0.1

    logger.info(f"Using audio device is {sd.default.device}")
    logger.info(f"Samplerate set to {fs}")
    logger.info(f"Sample length is {time}")

    logger.info("Opening laser interrupt to enable operation")

    laser_task.open_laser_interrupt()

    laser_task.laser_alignment_task(time, fs)
