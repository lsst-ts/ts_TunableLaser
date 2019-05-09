import argh
import argparse
import logging
import logging.handlers
from lsst.ts.tunablelaser.csc import LaserCSC
import asyncio


@argh.arg("-ll", "--log-level", choices=['info', 'debug'])
def start(log_level="info"):
    log = logging.getLogger()
    ch = logging.StreamHandler()
    fh = logging.handlers.TimedRotatingFileHandler('tunable_laser_csc.log',when='D')
    if log_level == "info":
        log.setLevel(logging.INFO)
        ch.setLevel(logging.INFO)
        fh.setLevel(logging.INFO)
    elif log_level == "debug":
        log.setLevel(logging.DEBUG)
        ch.setLevel(logging.DEBUG)
        fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
    ch.setFormatter(formatter)
    fh.setFormatter(formatter)
    log.addHandler(fh)
    log.addHandler(ch)
    laser = LaserCSC()
    sal_log=logging.getLogger(laser.log_name)
    sal_log.setLevel(logging.DEBUG)
    sal_log.addHandler(fh)
    log.debug(laser)
    log.info("TunableLaser CSC initialized")
    loop = asyncio.get_event_loop()
    try:
        log.info('Running CSC (Hit ctrl+c to stop it')
        loop.run_until_complete(laser.done_task)
        log.info('Stopping CSC')
    except KeyboardInterrupt as kbe:
        log.info("Stopping CBP CSC")
        log.exception(kbe)
    except Exception as e:
        log.error(e)
    finally:
        loop.close()


def create_parser():
    parser = argparse.ArgumentParser()
    argh.set_default_command(parser, start)
    return parser


def main():
    parser = create_parser()
    argh.dispatch(parser)


if __name__ == '__main__':
    main()
