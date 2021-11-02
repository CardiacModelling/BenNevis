#!/usr/bin/env python3
"""
Main module for Where's Ben Nevis (it's in Scotland).
"""
import sys

# Check Python version
if sys.hexversion < 0x03080000:
    raise RuntimeError('BenNevisServer requires Python 3.8 or newer.')

# Version number
__version__ = (0, 0, 1)

# Create public API
from ._data import (    # noqa
    ben,
    Coords,
    dimensions,
    gb,
    Hill,
    spacing,
    spline,
    pub,
)
from ._plot import (    # noqa
    plot,
    plot_line,
    png_bytes,
    save_plot,
)
from ._util import (    # noqa
    Timer,
)

# Don't exposure imported modules as part of the API
del(sys)
