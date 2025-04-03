import setuptools
import setuptools_scm

setuptools.setup(
    version=setuptools_scm.get_version(
        version_file="python/lsst/ts/tunablelaser/version.py",
        write_to="python/lsst/ts/tunablelaser/version.py",
        relative_to="pyproject.toml",
    )
)
