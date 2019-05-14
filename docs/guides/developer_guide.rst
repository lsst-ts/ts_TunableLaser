
Developer Guide
===============

The following guide is for a developer who wants to work on this project.


Installation
------------
This assumes that the following requirements are met.

* The latest version of centos 7 is installed
* The latest version of python 3.6 is installed.
* ts_sal installed according to sal_user_guide instructions.
* git repositories are in ~/gitrepo

.. code-block:: bash

    pip install -r requirements-dev.txt -e .
    export PYTHONPATH=$PYTHONPATH:~/gitrepo/ts_salobj/python
    source ~/gitrepo/ts_sal/setup.env

.. _`Design Decisions`:

Design Decisions
----------------
The code is written using python 3.6 as defined by the LSST standard. The unit tests are written in pytest in accordance
with the tssw python guide. Code contains both the component and CSC logic.

.. todo::
    Add link to tssw python guide when site location is finalized.

Component Decisions
+++++++++++++++++++
Component code is organized into a series of classes underneath the :mod:`lsst.ts.laser.hardware` namespace. The classes
themselves are essentially wrappers around the :term:`modules<module>` that make up the architecture of the laser. Each
class contains a :class:`lsst.ts.laser.ascii.AsciiRegister` which wrap around the :term:`registers<register>` of the
laser. Lets take a look at how to add registers.

The major source of truth regarding the permitted software functionality of the laser is located in the file
REMOTECONTROL.csv, which outlines all of the accessible modules and register to the developer. The section
:ref:`Reading REMOTECONTROL.csv<developer_guide:Reading REMOTECONTROL.csv>` will show how to do this.

Reading REMOTECONTROL.csv
^^^^^^^^^^^^^^^^^^^^^^^^^
The following list defines the relevant columns of this file.

Name
    The name of the module which is necessary for the Ascii protocol.
ID
    The ID of the module which is necessary for the Ascii protocol.
    A module can have more than one register which means that it can have more than one id.
Reg ID
    Doesn't matter.
Menu
    Doesn't matter.
Type
    Doesn't matter.
User Rights
    Anything with an r after it is read only.
Nonvolatile
    NV
        Stays in memory. Blank means resets after power off.
Min Value
    The minimum value of a register.
Max Value
    The maximum value of a register.
Short name
    Shorthand name for the register.
Print format
    Specifies the print format of the value of the register as well as the unit.
Name
    The name of the register which is important for the ascii protocol. Corresponds to the
    register name in ascii.
Value
    Example of the value of a register.

You'll notice that each register is defined by an AsciiRegister inside of the classes of the hardware module.

.. code-block:: python

    AsciiRegister(port,module_name,module_id,register_name,read_only,accepted_values,simulation_mode)


port
    A reference to the serial port which is connected to the laser.
module_name
    The name of the parent module which is necessary for formatting the register messages.
module_id
    The id of the parent module which serves the same purpose as the module_name.
register_name
    The name of the register.
read_only
    A register can be read_only or writable. An AsciiRegister has a default value of True and must be set to false in
    order to be writable.
accepted_values
    A list of accepted values by the register corresponds to the min and max values columns of the REMOTECONTROL.csv.
simulation_mode
    An attribute that needs to still be implemented.

.. todo::
    Add an example of contributing to code.

CSC Decisions
+++++++++++++
The CSC is written using ts_salobj. The CSC logic divided into a model class, which hooks up to the component logic and
the CSC class itself. Once simulation mode is implemented, the model class can have a flag that will set that up making
it easy to handle unit tests as well.

.. todo::
    Add links to ts_salobj documentation once location is finalized.

.. todo::
    Write :ref:`CSC Decisions<developer_guide:CSC Decisions>`.

Improvements
++++++++++++
* simulation mode
    A mode that would provide ideally realistic fake :term:`register` data. Useful for supporting CSC simulation mode as
    well as unit tests. Probably would need to add acceptable values attribute/parameter that could take a list like
    accepted values. The simulation_mode could be checked and if true, would use create_get_message to choose a value
    from the list. A potential problem with this approach would be values in the list that make no logical sense in a
    in a given context. However, this approach would at least give a good start to solving the problem at least on the
    hardware side.

.. todo::
    Think about serial port side of simulation mode

* Ascii commands
    The laser Ascii protocol supports commands that are not associated with a module. Its not been made necessary, but
    but it would make the API more supportive of the protocol's capabilites.
* Ascii logging
    A feature of the Ascii protocol is to support the logging of :term:`modules<module>`. Not necessary but would
    provide better API handling of the hardware.
* base module class
    It would be similar to the AsciiRegister class which each register is an instance of except that the module would
    inherit from this class rather than being instances of it.
* Register values as Python attributes
    Within modules add reference to register values as attributes.
* Add configuration mode attribute
    Add different configuration setup functionality. Preventing user error?

.. todo::
    Expand on :ref:`developer_guide:Improvements`

Unit Tests
++++++++++

.. todo::
    Write :ref:`developer_guide:Unit Tests`

.. todo::
    Rewrite :ref:`Design Decisions`





