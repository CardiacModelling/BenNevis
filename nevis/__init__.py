#!/usr/bin/env python3
"""
Main module for Where's Ben Nevis (it's in Scotland).
"""

#
# Version number
#
from ._nevis_version import (   # noqa
    __version__,
    __version_tuple__,
)

#
# Check Python version
#
import sys
if sys.hexversion < 0x03060000:
    raise RuntimeError('nevis requires Python 3.6 or newer.')
del(sys)    # Don't expose as part of API

#
# Installed project root
#
import os, inspect  # noqa
try:
    frame = inspect.currentframe()
    _DIR_MODULE = os.path.abspath(os.path.dirname(inspect.getfile(frame)))
    _DIR_MODULE_DATA = os.path.join(_DIR_MODULE, '_bin')
finally:
    # Always manually delete frame
    # https://docs.python.org/2/library/inspect.html#the-interpreter-stack
    del(frame)
del(os, inspect)    # Don't expose as part of API

#
# Terrain data
#
import os   # noqa

_ENV_DATA = 'NEVIS_PATH'
_DIR_DATA = os.environ.get(_ENV_DATA)
if _DIR_DATA is None:
    _DIR_DATA = os.path.join('~', 'nevis-data')
_DIR_DATA = os.path.abspath(os.path.expanduser(_DIR_DATA))
del(os)


#
# Create public API
#
from ._bng import (    # noqa
    ben,
    Coords,
    dimensions,
    fen,
    Hill,
    pub,
    squares,
)
from ._os50 import (    # noqa
    DataNotFoundError,
    download_os50,
    gb,
    spacing,
)
from ._interpolation import (   # noqa
    linear_interpolant,
    spline,
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


#
# Version-related methods
#
def howdy(name='Local'):
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


#
# Test method
#
def write_test_figure(path='gb-small.png'):
    """
    Create a write a test figure.
    """
    gb()
    labels = {'Ben Nevis': ben(), 'Holme Fen': fen()}
    fig, ax, heights, g = plot(labels=labels, downsampling=32)
    save_plot(path, fig, silent=False)

