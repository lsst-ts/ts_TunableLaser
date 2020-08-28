############
TunableLaser
############

.. image:: https://img.shields.io/badge/SAL-API-gray.svg
    :target: https://ts-xml.lsst.io/sal_interfaces/TunableLaser.html
.. image:: https://img.shields.io/badge/GitHub-gray.svg
    :target: https://github.com/lsst-ts/ts_TunableLaser
.. image:: https://img.shields.io/badge/Jira-gray.svg
    :target: https://jira.lsstcorp.org/issues/?jql=labels+%3D+ts_TunableLaser
.. image:: https://img.shields.io/badge/Jenkins-gray.svg
    :target: https://tssw-ci.lsst.org/job/LSST_Telescope-and-Site/job/ts_TunableLaser/


.. _Overview:

Overview
========

:ref:`Contact info <ts_xml:index:master-csc-table:TunableLaser>`

The Tunable Laser CSC is used to control an Ekspla NT-242 laser via the Rubin Observatory Control System.
The laser is used to send light via a fiber to the `Collimated Beam Projector <https://ts-cbp.lsst.io>`_ and the Calibration Screen Illumination System, which is used to perform flat fielding.
The CSC provides commands to change the wavelength, start and stop the propagation of the laser.
It also provides the capability of selecting where the laser light is directed (CBP or Calibration Screen).

.. note:: If you are interested in viewing other branches of this repository append a `/v` to the end of the url link. For example ``https://ts-tunable-laser.lsst.io/v/``


.. _index:user-documentation:

User Documentation
==================

User-level documentation, found at the link below, is aimed at personnel looking to perform the standard use-cases/operations with the TunableLaser.

.. toctree::
    user-guide/user-guide
    :maxdepth: 2

.. _index:configuration:

Configuring the TunableLaser
============================

The configuration for the TunableLaser is described at the following link.

.. toctree::
    configuration/configuration
    :maxdepth: 1


.. _index:development-documentation:

Development Documentation
=========================

This area of documentation focuses on the classes used, API's, and how to participate to the development of the TunableLaser software packages.

.. toctree::
    developer-guide/developer-guide
    :maxdepth: 1

.. _index:version_history:

Version History
===============

The version history of the TunableLaser is found at the following link.

.. toctree::
    version-history
    :maxdepth: 1
