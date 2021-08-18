__all__ = ["CONFIG_SCHEMA"]

import yaml

CONFIG_SCHEMA = yaml.safe_load(
    """
$schema: http://json-schema.org/draft-07/schema#
$id: https://github.com/lsst-ts/ts_TunableLaser/blob/master/schema/TunableLaser.yaml
title: TunableLaser v1
description: Schema for TunableLaser configuration files
type: object
properties:
  host:
    description: Host for the TCPIP server
    type: string
    default: "127.0.0.1"
  port:
    description: Port for the TCPIP server.
    type: integer
    default: 9999
  timeout:
    description: Timeout for the TCPIP client.
    type: number
    default: 1
  optical_configuration:
    description: The mirror alignment configuration for the laser
    enum: ["straight-through","F1","F2"]
    default: "straight-through"
  wavelength:
    description: The min and max wavelengths for the laser
    type: object
    properties:
      min:
        type: integer
        minimum: 300
        maximum: 1100
        default: 300
      max:
        type: integer
        minimum: 300
        maximum: 1100
        default: 1100
"""
)
