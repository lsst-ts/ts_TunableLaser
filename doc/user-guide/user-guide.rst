..
  This is a template for the user-guide documentation that will accompany each CSC.
  This template is provided to ensure that the documentation remains similar in look, feel, and contents to users.
  The headings below are expected to be present for all CSCs, but for many CSCs, additional fields will be required.

  ** All text in square brackets [] must be re-populated accordingly **

  See https://developer.lsst.io/restructuredtext/style.html
  for a guide to reStructuredText writing.

  Use the following syntax for sections:

  Sections
  ========

  and

  Subsections
  -----------

  and

  Subsubsections
  ^^^^^^^^^^^^^^

  To add images, add the image file (png, svg or jpeg preferred) to the
  images/ directory. The reST syntax for adding the image is

  .. figure:: /images/filename.ext
   :name: fig-label

   Caption text.

  Feel free to delete this instructional comment.

.. Fill out data so contacts section below is auto-populated
.. add name and email between the *'s below e.g. *Marie Smith <msmith@lsst.org>*
.. |CSC_developer| replace::  *Replace-with-name-and-email*
.. |CSC_product_owner| replace:: *Replace-with-name-and-email*

.. _User_Guide:

#######################
TunableLaser User Guide
#######################

XML location can be found at the top of the :doc:`index </index>`

The laser is a class 4 laser system according to the international laser committee.
This means that the laser must have an interlock system that prevents unintended propagation of the laser.
As the beam is powerful enough to cause damage to the eyes of anyone who looks into the light.
Various safety measures have been enacted to prevent this from happening.
This guide does not cover that information as that is under the purview of the Laser Safety Officer.
The CSC goes into a fault state when the interlock system is tripped.
This means that the clearFaultState command should be sent in order to return the laser to its nominal state.
Then the normal standby command should be issued to bring the CSC out of fault state.

The TunableLaser CSC provides commands for changing the wavelength and configuration output of the laser.
It has two output paths, one where the output goes through the Spectral Cleaning Unit(SCU) and one where it does not.
Then there are three holes that the beam can come out of.

* Straight-through
* Fiber one
* Fiber two

Physically, the laser has to be moved in order to use the SCU or not, so that value is not controlled at the CSC level.
Otherwise, the beam would cause serious damage to the internals of the laser.
The output holes are controlled by the CSC level as there are mirrors which control the direction of the beam in the laser.
The laser has a range of 300 to 1100 nm for wavelength changing.


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
