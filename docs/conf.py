"""Sphinx configuration file for an LSST stack package.

This configuration only affects single-package Sphinx documentation builds.
"""

from pkg_resources import get_distribution
from documenteer.sphinxconfig.stackconf import build_package_configs
import lsst.ts.laser

_g = globals()
_g.update(build_package_configs(
    project_name='ts_tunablelaser',
    version=get_distribution('ts-tunablelaser').version))
intersphinx_mapping['ts_salobj']=('http://staff.washington.edu/rowen/ts_salobj/',None)
extensions.append('sphinxcontrib.confluencebuilder')
todo_include_todos=False
