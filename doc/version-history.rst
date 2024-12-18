.. _Version_History:

===============
Version History
===============

.. towncrier release notes start

ts_tunablelaser v2.2.1 (2024-12-18)
===================================

Bugfixes
--------

- Added retry attempt in case of communication instability. (`DM-47555 <https://rubinobs.atlassian.net/DM-47555>`_)


ts_tunablelaser v2.2.0 (2024-11-26)
===================================

Features
--------

- Changed optical configuration so that it takes SCU/No SCU rather than being hard coded. (`DM-44592 <https://rubinobs.atlassian.net/DM-44592>`_)
- Hooking up the thermal ctrl telemetry to CSC (`dm-44146 <https://rubinobs.atlassian.net/dm-44146>`_)


Bugfixes
--------

- Fixing two bugs with thermal ctrl system. The first is that if its not connected there is a chance it tries to access a None method. The second bug is that it improperly parses results. (`dm-44396 <https://rubinobs.atlassian.net/dm-44396>`_)


Misc
----

- `DM-44083 <https://rubinobs.atlassian.net/DM-44083>`_


ts_tunablelaser v2.1.1 (2024-04-11)
===================================

Bugfixes
--------

- Update port for TempCtrlServer to support dynamic ports to avoid restricted port 50. (`DM-43844 <https://rubinobs.atlassian.net/DM-43844>`_)
- Add noarch to Jenkinsfile.conda file. (`DM-43844 <https://rubinobs.atlassian.net/DM-43844>`_)


ts_tunablelaser v2.1.0 (2024-04-11)
===================================

Features
--------

- Implmented do_setOpticalConfiguration to allow on-the-fly change changes to the optical configuration. Implemented supporting function in MainLaser component, as well as tracking which laser is being used. (`DM-41426 <https://rubinobs.atlassian.net/DM-41426>`_)
- Adding the E5DC_B class to support the omron temperature sensor over the CompoWayF protocol (`dm-37871 <https://rubinobs.atlassian.net/dm-37871>`_)
- Adding the csc support for the E5DC_B. Adding temp_ctrl_server to give the E5DC_B a separate host/port pathway. Adding all the necessary support for that to config, mock_server, etc... (`dm-42113 <https://rubinobs.atlassian.net/dm-42113>`_)
- Updating various parts of the code to make it work in the real world lab. This consists of: decoding all bytes and handling everything in strings exclusively. 2's complement, hex values for set point sending, and other various fixes. (`dm-42903 <https://rubinobs.atlassian.net/dm-42903>`_)


Bugfixes
--------

- Call setOpticalConfiguration when connecting to the device (CSC disabled->enabled) which means when the laser is ready to be used it will be in the configured optical configuration. (`DM-40029 <https://rubinobs.atlassian.net/DM-40029>`_)
- Update ts-conda-build to 0.4. (`DM-43486 <https://rubinobs.atlassian.net/DM-43486>`_)


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
