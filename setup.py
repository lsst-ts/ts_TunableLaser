from setuptools import setup
setup_reqs=["setuptools_scm"]
install_reqs=["pyserial","argh"]
test_reqs=["pytest","pytest-flake8","pytest-cov","pytest-mock"]
dev_reqs=setup_reqs+install_reqs+test_reqs+["documenteer[pipelines]"]
setup(
    name="ts-tunablelaser",
    setup_requires=setup_reqs,
    install_requires=install_reqs,
    package=['lsst.ts.tunablelaser'],
    extras_require={'dev':dev_reqs}
)
