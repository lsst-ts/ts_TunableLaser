#######################
TunableLaser User Guide
#######################

XML location can be found at the top of the :doc:`top of this page </index>`.

The laser is a class 4 laser system according to the international laser committee.
This means that the laser must have an interlock system that prevents unintended propagation of the laser as the beam is powerful enough to cause damage to the eyes of anyone who looks into the light.
Various safety measures have been enacted to prevent this from happening.
This guide does not cover that information as that is under the purview of the Laser Safety Officer [Patrick Ingraham].
If the interlock is tripped, then the laser will stop propagating and the CSC will transition to the fault state.
Upon clearing the interlock, send the clearFaultState command in order to return the laser to its nominal state.
Then the normal standby command should be issued to bring the CSC out of fault state.

The TunableLaser CSC provides commands for changing the wavelength and configuration output of the laser.
It has two output paths, one where the output goes through the Spectral Cleaning Unit(SCU) and one where it does not.
Then there are three separate exit ports for the beam.

* Straight-through
* Fiber one
* Fiber two

Physically, the laser has to be moved in order to use the SCU or not, so that value is not controlled at the CSC level.
Otherwise, the beam would cause serious damage to the internals of the laser.
The output holes are controlled by the CSC level as there are mirrors which control the direction of the beam in the laser.
The laser has a range of 300 to 1100 nm for wavelength changing.

.. _developer-guide:developer-guide:tunablelaser-interface:

TunableLaser Interface
======================

The primary commands are

:ref:`ts_xml:TunableLaser:Commands:changeWavelength`

:ref:`ts_xml:TunableLaser:Commands:startPropagateLaser`

:ref:`ts_xml:TunableLaser:Commands:stopPropagateLaser`

The primary events are

:ref:`ts_xml:TunableLaser:Events:wavelengthChanged`

:ref:`ts_xml:TunableLaser:Events:laserInstabilityFlag`

Pertinent telemetry

:ref:`ts_xml:TunableLaser:Telemetry:temperature`

:ref:`ts_xml:TunableLaser:Telemetry:wavelength`

.. _developer-guide:developer-guide:example-use-case:

Example Use-Case
================

.. code::

    from lsst.ts import salobj

    tunable_laser = salobj.Remote(name="TunableLaser", domain=salobj.Domain())

.. code::

    await tunable_laser.cmd_changeWavelength.set_start(wavelength=635, timeout=20)
    await tunable_laser.cmd_startPropagateLaser.set_start(timeout=20)
    await tunable_laser.cmd_stopPropagateLaser.set_start(timeout=20)

.. code::

    wavelength = await tunable_laser.tel_wavelength.aget()
    temperature = await tunable_laser.tel_temperature.aget()
