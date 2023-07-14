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

__all__ = ["CONFIG_SCHEMA"]

import yaml

CONFIG_SCHEMA = yaml.safe_load(
    """
$schema: http://json-schema.org/draft-07/schema#
$id: https://github.com/lsst-ts/ts_TunableLaser/blob/master/schema/TunableLaser.yaml
title: TunableLaser v2
description: Schema for TunableLaser configuration files
type: object
properties:
  host:
    description: Host for the TCPIP server
    type: string
  port:
    description: Port for the TCPIP server.
    type: integer
  timeout:
    description: Timeout for the TCP/IP client.
    type: number
  optical_configuration:
    description: The mirror alignment configuration for the laser
    enum: ["straight-through","F1","F2"]
  wavelength:
    description: The min and max wavelengths for the laser
    type: object
    properties:
      min:
        type: integer
        minimum: 300
        maximum: 1100
      max:
        type: integer
        minimum: 300
        maximum: 1100
    required:
      - min
      - max
    addtionalProperties: false
required:
  - host
  - port
  - timeout
  - optical_configuration
  - wavelength
additionalProperties: false
"""
)
