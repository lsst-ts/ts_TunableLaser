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
    asyncio.run(LaserAlignmentListener.amain(index=None))


class LaserAlignmentListener(tcpip.OneClientServer):
    def __init__(
        self,
        logger: logging.Logger,
        port: int | None = 1883,
        host: str | None = tcpip.DEFAULT_LOCALHOST,
        encoding: str = tcpip.DEFAULT_ENCODING,
        terminator: bytes = tcpip.DEFAULT_TERMINATOR,
        sample_wait_time=60,
        serial=None,
        temperature_windows=8,
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

        self.config()

    def config(self):
        self.relay_gpio = 7
        self.configured = True
        self.pi = pigpio.pi()

    async def amain(self):
        self.laser_alignment_task()

    def publish_msg(self, msg):
        self.pending_messages.append(msg)
        self.read_and_dispatch()

    def read_and_dispatch(self):
        # read data
        # incoming_data = self.read_str()
        # handle data

        # send data
        while len(self.pending_messages) != 0:
            self.write_str(self.pending_messages.pop() + self.terminator)

    def record_data(self, duration, fs):
        self.logger.debug("Check input settings")
        sd.check_input_settings(device=input, samplerate=fs, channels=1)
        self.logger.debug(f"Starting to record for {duration} seconds")
        data = sd.rec(
            frames=int(duration * fs), samplerate=fs, channels=1, blocking=True
        )
        return data

    def analyze_data(self, data, fs):
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

    def set_relay(self, setting):
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

    def laser_alignment_task(self, time, fs):
        try:
            self.logger.info("Starting monitoring task")

            FILEFOLDER = "./logs"
            FILENAME = "laser_alignment"

            # Declare how many iterations have to be
            # above the threshold to shut off the laser
            count_threshold = 7  # 10
            count = 0

            # TODO remove debug csv
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
