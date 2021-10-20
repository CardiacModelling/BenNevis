#!/usr/bin/env python3
"""
Main module for Where's Ben Nevis (it's in Scotland).
"""
import sys

# Check Python version
if sys.hexversion < 0x03050000:
    raise RuntimeError('This script requires Python 3.5 or newer.')

# Version number
__version__ = (0, 0, 1)

# Create public API
from ._data import (    # noqa
    gb,
)
from ._plot import (    # noqa
    plot,
    save_plot,
)
from ._util import (    # noqa
    Timer,
)

# Don't exposure imported modules as part of the API
del(sys)
