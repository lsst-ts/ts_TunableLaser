"""Sphinx configuration file for an LSST stack package.

This configuration only affects single-package Sphinx documentation builds.
"""

from documenteer.sphinxconfig.stackconf import build_package_configs
import lsst.ts.tunablelaser

_g = globals()
_g.update(build_package_configs(
    project_name='ts_tunablelaser',
    version=lsst.ts.tunablelaser.__version__))

intersphinx_mapping['ts_salobj'] = ('https://ts-salobj.lsst.io', None)
