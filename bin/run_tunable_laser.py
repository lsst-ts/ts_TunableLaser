#!/usr/bin/env python

import asyncio

from lsst.ts.tunablelaser.csc import LaserCSC

asyncio.run(LaserCSC.amain(index=None))
