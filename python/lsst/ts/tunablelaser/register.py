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

"""Implements Ascii helper classes for the TunableLaser.

These classes are meant to aid in developing a python wrapper around the ascii
spec used by Ekspla to communicate with the TunableLaser.

Notes
-----
The most important class in this module is `AsciiRegister`, which defines the
ASCII messages used to read and write laser registers.

"""

__all__ = ["AsciiRegister"]
import logging


class AsciiRegister:
    """A representation of an Ascii register inside of a module of the laser.

    The class corresponds to a register within a module of a laser. A register
    can be read only or writable.
    If it is read only then the ``accepted_values`` argument is ignored.

    Parameters
    ----------
    module_name : `str`
        The name of the module that is the parent of the register.
    module_id : `int`
        The id of the module that is the parent of the register.
    register_name : `str`
        The name of the register.
    read_only : `bool`, optional
        Whether the register is read only or writable.
    accepted_values : `list` [`str`] or `list` [`int`] or `None`, optional
        If read_only is set to true then this parameter can be None. If not,
        this parameter must contain a list of values accepted by this
        register and can be of int or str.
    Attributes
    ----------
    log : `logging.Logger`
        The log for this class.
    module_name : `str`
        The name of the module that is the parent of the register.
    module_id : `int`
        The id of the module that is the parent of the register.
    register_name : `str`
        The name of the register.
    read_only : `bool`
        Whether the register is read only or writable.
    accepted_values : `list`
        If read_only is set to true then this parameter can be None.
        If not, this parameter must contain a list of values accepted by this
        register and can be of int or str.
    register_value : `str`
        Cached value most recently read from or written through the owning
        controller.

    """

    def __init__(
        self,
        module_name,
        module_id,
        register_name,
        read_only=True,
        accepted_values=None,
    ):
        self.log = logging.getLogger(f"{register_name.replace(' ', '')}Register")
        self.module_name = module_name
        self.module_id = module_id
        self.register_name = register_name
        self.read_only = read_only
        if not self.read_only and accepted_values is None:
            raise AttributeError("If read_only is false than accepted_values should not be None.")
        self.accepted_values = accepted_values
        self._register_value = None
        self.log.debug(f"{self.register_name} Register initialized")

    @property
    def register_value(self):
        return self._register_value

    @register_value.setter
    def register_value(self, value):
        self._register_value = value

    def create_get_message(self):
        """Generate the message that will get the register value.

        Returns
        -------
        get_message: `bytes`

        """
        get_message = f"/{self.module_name}/{self.module_id}/{self.register_name}\r"
        self.log.debug(f"get_message={get_message}")
        return get_message

    def create_set_message(self, set_value):
        """Create the message that sets the value of the register provided
        that it is not read only.

        Parameters
        ----------
        set_value : Any

        Raises
        ------
        ReadOnlyException
            Indicates that the register is read only.
        ValueError
            Indicates that the value received is not in the acceptable values
            for the register.

        Returns
        -------
        set_message : `bytes`

        """
        if not self.read_only:
            if set_value not in self.accepted_values:
                raise ValueError(f"{set_value} not in {self.accepted_values}")
            set_message = f"/{self.module_name}/{self.module_id}/{self.register_name}/{set_value}\r"
            self.log.debug(f"set_message={set_message}")
            return set_message
        else:
            raise PermissionError("This register is read only.")

    def __repr__(self):
        return "{}: {}".format(self.register_name, self.register_value)
