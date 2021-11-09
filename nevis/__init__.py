#!/usr/bin/env python3
"""
Main module for Where's Ben Nevis (it's in Scotland).
"""
import sys

# Check Python version
if sys.hexversion < 0x03060000:
    raise RuntimeError('BenNevisServer requires Python 3.6 or newer.')

# Version number
__version_tuple__ = (0, 0, 2)
__version__ = '.'.join(str(x) for x in __version_tuple__)

# Create public API
from ._data import (    # noqa
    ben,
    Coords,
    dimensions,
    fen,
    gb,
    Hill,
    spacing,
    spline,
    squares,
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


def howdy(name='Server'):
    """ Say hi the old fashioned way. """
    print('')
    print('                |>          ')
    print(' Starting Ben   |   Nevis   ')
    print('               / \    ' + name)
    print('            /\/---\     ' + __version__)
    print('           /---    \/\      ')
    print('        /\/   /\   /  \     ')
    print('     /\/  \  /  \_/    \    ')
    print('    /      \/           \   ')


# Don't exposure imported modules as part of the API
del(sys)
