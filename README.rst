###############
ts-TunableLaser
###############

The TunableLaser is a CSC for the `Vera C. Rubin Observatory <https://www.lsst.org>`_.
It controls a laser for the Main Telescope Calibration System.

`Documentation <https://ts-tunablelaser.lsst.io>`_

Installation
============

.. code::

    setup -kr .
    scons
    python runTunableLaserCSC.py

.. code::

    pip install .[dev]
    python runTunableLaserCSC.py

Requirements
------------
This project uses the ``black`` linter.

Run the following once in the repository

.. code::

    git config core.hooksPath .githooks
    chmod +x .githooks/pre-commit
    

Usage
=====

Start up the remote for commanding the CSC

.. code::

    from lsst.ts import salobj
    tunable_laser = salobj.Remote(name="TunableLaser", domain=salobj.Domain())
    await tunable_laser.start_task

How to command the CSC

.. code::

    await tunable_laser.cmd_startPropagateLaser.set_start(timeout=10)
    await tunable_laser.cmd_stopPropagateLaser.set_start(timeout=10)
    await tunable_laser.cmd_changeWavelength.set_start(wavelength=650, timeout=10)

Getting the events from the CSC

.. code::

    laser_instability = await tunable_laser.evt_laserInstabilityFlag.aget()
    wavelength_changed = await tunable_laser.evt_wavelengthChanged.aget()

Getting the telemetry from the CSC

.. code::

    wavelength = await tunable_laser.tel_wavelength.aget()
    temperature = await tunable_laser.tel_temperature.aget()

Support
=======
Contact info for developer(s) and product owner.
Use the `Jira project <https://jira.lsstcorp.org>`_ to file tickets under the ``ts_TunableLaser`` label

Roadmap
=======
N/A

Contributing
============
Check the developer guide for help finding out how to contribute to this project.

License
=======
This project is released under the `GPL V3 License <https://www.gnu.org/licenses/gpl-3.0.en.html>`_.