from setuptools import setup

setup(
    name="ts-tunablelaser",
    setup_requires=['setuptools-scm'],
    install_requires=["pyserial==3.4"],
    use_scm_version=True,
    package=['lsst.ts.laser'],
)