
User's Guide
============

The following page will instruct the user in how to use the TunableLaser CSC.

Establishing Connection to Hardware
-----------------------------------
* plug in usb cable into usb device port on Laser's power supply
* default connection goes to /dev/ttyACM0

.. todo::
    Write udev rule for symlinking to /dev/ttyTunableLaser


Running CSC
-----------

On the machine where the TunableLaser is connected run the following command.

.. code-block:: bash

    laser_csc /dev/ttyACM0


The user should see some output saying that the laser CSC is running and start seeing telemetry being sent.

Sending Commands
----------------

.. code-block:: python

    import asyncio
    import salobj
    import SALPY_TunableLaser


    async def main():
        # initialize remote
        laser_remote = salobj.Remote(SALPY_TunableLaser)

        # get telemetry
        await laser_remote.tel_wavelength.next(timeout=10)
        await laser_remote.tel_temperature.next(timeout=10)

        # send commands
        start_laser_topic = laser_remote.cmd_start.DataType() # this is how the topic is started
        start_laser_ack = await laser_remote.cmd_start.start(start_laser_topic,timeout=10) #timeout is in case command is not acknowledged.
        print(start_laser_ack) # this prints the acknowledgement code if there is one.

        # send commands with parameters
        change_wavelength_topic = laser_remote.cmd_changeWavelength.DataType()
        change_wavelength_topic.wavelength = 550 # in nanometers
        change_wavelength_ack = await laser_remote.cmd_changeWavelength.start(change_wavelength_topic,timeout=10)
        print(change_wavelength_ack)

        # Not sure of a good use case for multiple commands sent at once

        # exiting csc control
        exit_control_topic = laser_remote.cmd_exitControl.DataType()
        exit_control_ack = await laser_remote.cmd_exitControl.start(exit_control_topic)

    if __name__ == "__main__":
        asyncio.get_event_loop().run_until_complete(main()) # this is how you start actually running commands and receiving telemetry


Primarily, this is how one will interact with this lower level CSC.

Shutting down CSC
-----------------
Hit ctrl+c on the running laser_csc process. Work in progress

.. todo::
    Figure out what needs to be done to improve this page.

