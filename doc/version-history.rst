.. _Version_History:

===============
Version History
===============

.. towncrier release notes start

ts_tunablelaser 2.0.1 (2024-01-08)
==================================

Bugfixes
--------

- Add parameterized to testing section in conda recipe. (`DM-42375 <https://jira.lsstcorp.org/DM-42375>`_)


ts_tunablelaser 2.0.0 (2023-12-15)
==================================

Features
--------

- Added Laser class that all laser components inherit from. (`DM-41074 <https://jira.lsstcorp.org/DM-41074>`_)
- Added a CanbusModule base class for canbus_modules module. (`DM-41074 <https://jira.lsstcorp.org/DM-41074>`_)
- Renamed Component to MainLaser. (`DM-41074 <https://jira.lsstcorp.org/DM-41074>`_)
- Added required type field to configuration schema. (`DM-41074 <https://jira.lsstcorp.org/DM-41074>`_)
- Added StubbsLaser class and related modules. (`DM-41074 <https://jira.lsstcorp.org/DM-41074>`_)


Improved Documentation
----------------------

- Added towncrier. (`DM-41074 <https://jira.lsstcorp.org/DM-41074>`_)


v1.0.1
======

* Support tcpip 2.0.

v1.0.0
======
* Initial release.
