"""Sphinx configuration file for TSSW package"""

from documenteer.conf.pipelinespkg import *

project = "ts_tunablelaser"
html_theme_options["logotext"] = project
html_title = project
html_short_title = project

intersphinx_mapping["ts_xml"] = ("https://ts-xml.lsst.io", None)
intersphinx_mapping["ts_salobj"] = ("https://ts-salobj.lsst.io", None)
intersphinx_mapping["ts_tcpip"] = ("https://ts-tcpip.lsst.io", None)
