#!/usr/bin/env python3
"""
Provides plotting methods.
"""
# The zip contains several grid squares, using the lettering described here:
# https://en.wikipedia.org/wiki/Ordnance_Survey_National_Grid
#
# Inspired by
# https://scipython.com/blog/processing-uk-ordnance-survey-terrain-data/
#
import numpy as np

import matplotlib.colors
import matplotlib.pyplot as plt


def plot(arr, downsampling=27):
    """
    Creates a plot of the 2D elevation data in ``arr``, downsampled with a
    factor ``downsampling``.

    Returns a tuple ``(fig, ax, arr)`` where ``fig`` is the created figure,
    ``ax`` is the axes the image is plotted on, and ``arr`` is the downsampled
    numpy array.
    """
    ny, nx = arr.shape

    # Get extreme points
    vmin = np.min(arr)
    vmax = np.max(arr)
    print(f'Highest point: {vmax}')

    # Downsample (27 gives me a map that fits on my screen at 100% zoom).
    if downsampling > 1:
        print(f'Downsampling with factor {downsampling}')
        nx, ny = nx // downsampling, ny // downsampling
        arr = arr[::downsampling, ::downsampling]

    # Plot
    print('Plotting...')

    # Create colormap
    # f = absolute height, g = relative to vmax (and zero)
    f = lambda x: (x - vmin) / (vmax - vmin)
    # g = lambda x: f(x * vmax)
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list(
        'soundofmusic', [
            (0, '#78b0d1'),             # Deep sea blue
            (f(-4.0), '#78b0d1'),       # Deep sea blue
            (f(-3), '#0f561e'),         # Dark green
            (f(10), '#1a8b33'),         # Nicer green
            (f(100), '#11aa15'),        # Glorious green
            (f(300), '#e8e374'),        # Yellow at ~1000ft
            (f(610), '#8a4121'),        # Brownish at ~2000ft
            (f(915), '#999999'),       # Grey at ~3000ft
            (1, 'white'),
        ])

    # Work out figure dimensions
    dpi = 600
    fw = nx / dpi
    fh = ny / dpi
    print(f'Figure dimensions: {fw}" by {fh}" at {dpi} dpi')
    print(f'Should result in {nx} by {ny} pixels.')

    fig = plt.figure(figsize=(fw, fh), dpi=dpi)
    fig.subplots_adjust(0, 0, 1, 1)
    ax = fig.add_subplot(1, 1, 1)
    ax.set_axis_off()
    ax.imshow(
        arr,
        origin='lower',
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
    )

    return fig, ax, arr


def save_plot(path, fig, arr):
    """
    Stores the given figure using ``fig.savefig(path)``, but will also check
    that the image dimensions (in pixels) equal the size of ``arr``.

    This check requires ``PIL`` to be installed (will silently fail if not).
    """
    fig.savefig(path)
    try:
        import PIL
    except ImportError:
        return

    im = PIL.Image.open(path)
    print(f'Checking PNG size with PIL: {im.size[0]} by {im.size[1]}')
    ny, nx = arr.shape
    if im.size[0] == nx or im.size[1] != ny:
        print('Image size OK')
    else:
        print('Unexpected image size!')

