#!/usr/bin/env python

import argparse
import logging
import signal

from lsst.ts.laser.statemachine import LaserCSC

__all__ = ["main"]

LOG_LEVEL = [logging.ERROR, logging.INFO, logging.DEBUG]


def create_parser():
    """Create parser
    """
    description = ["This is the main driver script for the LSST OCS scripts."]

    parser = argparse.ArgumentParser(usage="run_sequence.py [options]",
                                     description=" ".join(description),
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("-v", "--verbose", dest="verbose", action='count', default=0,
                        help="Set the verbosity for the console logging.")
    parser.add_argument("-c", "--console-format", dest="console_format", default=None,
                        help="Override the console format.")
    parser.add_argument("port",metavar="PORT",nargs=1,type=str,help="The port of the laser")

    return parser


def main(args):
    """
    Main method to startup OCS scripts in python.
    :param args:
    :return:
    """

    level = LOG_LEVEL[args.verbose] if args.verbose < 3 else logging.DEBUG

    logging.basicConfig(level=level, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")
    logging.captureWarnings(True)

    log = logging.getLogger(__name__)

    csc = LaserCSC(args.port[0])

    log.info('Running CSC (Control+C to stop it)...')

    signal.signal(signal.SIGTERM, csc.stop_csc)
    signal.signal(signal.SIGINT, csc.stop_csc)

    try:
        csc.run()
        signal.pause()
    except KeyboardInterrupt as e:
        log.info('Stopping %s CSC.', args.subsystem_tag)

    return 0


if __name__ == '__main__':
    parser = create_parser()
    args = parser.parse_args()

    main(args)
