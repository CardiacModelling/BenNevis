#!/usr/bin/env python3
"""
Main module for Where's Ben Nevis (it's in Scotland).
"""
import inspect
import os
import sys

# Check Python version
if sys.hexversion < 0x03080000:
    raise RuntimeError('This module requires Python 3.8 or newer.')

# Version number
__version__ = (0, 0, 1)

# Path to this module
try:
    frame = inspect.currentframe()
    DIR_NEVIS = os.path.abspath(os.path.dirname(inspect.getfile(frame)))
finally:
    del(frame)

# Create public API
from ._data import (    # noqa
    ben,
    gb,
    Coords,
    Hill,
)
from ._plot import (    # noqa
    plot,
    save_plot,
)
from ._util import (    # noqa
    Timer,
)

# Don't exposure imported modules as part of the API
del(inspect, os, sys)
