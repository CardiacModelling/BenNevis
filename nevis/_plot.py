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
import matplotlib.colors
import matplotlib.figure
import numpy as np

import nevis


def plot(arr, boundaries=None, labels=None, trajectory=None, points=None,
         scale_bar=True, downsampling=27, silent=False):
    """
    Creates a plot of the 2D elevation data in ``arr``, downsampled with a
    factor ``downsampling``.

    Returns a tuple ``(fig, ax, arr)`` where ``fig`` is the created figure,
    ``ax`` is the axes the image is plotted on, and ``arr`` is the downsampled
    numpy array.

    Arguments:

    ``arr``
        The terrain data.
    ``boundaries``
        An optional tuple ``(xmin, xmax, ymin, ymax)`` defining the boundaries
        (in meters) of the plotted region.
    ``labels``
        An optional dictionary mapping string labels to points (tuples in
        meters or Coords objects) that will be plotted on the map (if within
        the boundaries).
    ``trajectory``
        An optional array of shape ``(n_points, 2)`` indicating the trajectory
        followed to get to Ben Nevis (points specified in meters).
    ``points``
        An optional array of shape ``(n_points, 2)`` indicating points on the
        map (points specified in meters).
    ``scale_bar``
        Set to ``False`` to disable the scale bar.
    ``downsampling``
        Set to any integer to set the amount of downsampling (the ratio of data
        points to pixels in either direction).
    ``boundaries``
        An optional

    ``silent``
        Set to ``True`` to stop writing a status to stdout.

    """
    # Current array shape
    ny, nx = arr.shape

    # Get extreme points (before any downsampling!)
    vmin = np.min(arr)
    vmax = np.max(arr)
    if not silent:
        print(f'Highest point: {vmax}')

    # Downsample (27 gives me a map that fits on my screen at 100% zoom).
    if downsampling > 1:
        if not silent:
            print(f'Downsampling with factor {downsampling}')
        arr = arr[::downsampling, ::downsampling]
        ny, nx = arr.shape
        print(ny, nx, downsampling)

    # Select region to plot, and create meters2indices method
    d_org = d_new = np.array(nevis.dimensions())    # In meters
    offset = np.array([0, 0])                       # In meters
    if boundaries is not None:
        xlo, xhi, ylo, yhi = [float(x) for x in boundaries]

        # Select appropriate part of array
        xlo = max(0, int(xlo / d_org[0] * nx))
        ylo = max(0, int(ylo / d_org[1] * ny))
        xhi = 1 + min(nx, int(np.ceil(xhi / d_org[0] * nx)))
        yhi = 1 + min(ny, int(np.ceil(yhi / d_org[1] * ny)))
        arr = arr[ylo:yhi, xlo:xhi]

        # Adjust array size
        ny, nx = arr.shape

        # Set new dimensions and origin (bottom left)
        r = nevis.spacing() * downsampling
        d_new = np.array([nx * r, ny * r])
        offset = np.array([xlo * r, ylo * r])

    def meters2indices(x, y):
        """ Convert meters to array indices (which equal image coordinates) """
        x = (x - offset[0]) / d_new[0] * nx
        y = (y - offset[1]) / d_new[1] * ny
        try:
            x, y = int(x), int(y)
        except TypeError:
            x, y = x.astype(int), y.astype(int)
        return x, y

    # Plot
    if not silent:
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
            (f(915), '#999999'),        # Grey at ~3000ft
            (1, 'white'),
        ])

    # Work out figure dimensions
    dpi = 200
    fw = nx / dpi
    fh = ny / dpi
    if not silent:
        print(f'Figure dimensions: {fw}" by {fh}" at {dpi} dpi')
        print(f'Should result in {nx} by {ny} pixels.')

    fig = matplotlib.figure.Figure(figsize=(fw, fh), dpi=dpi)
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
    ax.set_xlim(0, nx)
    ax.set_ylim(0, ny)

    # Add scale bar
    if scale_bar:
        # Guess a good size
        x = d_new[0] / 7
        if x > 250e3:
            x = int(round(x / 250e3) * 250e3)
        elif x > 90e3:
            x = int(round(x / 100e3) * 100e3)
        elif x > 9e3:
            x = int(round(x / 10e3) * 10e3)
        elif x > 2e3:
            x = int(round(x / 5e3) * 5e3)
        elif x > 1e3:
            x = int(round(x / 1e3) * 1e3)
        else:
            x = int(round(x / 100) * 100)
        t = f'{x}m' if x < 1000 else f'{x // 1000}km'
        x = x / d_new[0] * nx
        y = 0.05 * ny
        dy = 0.01 * ny
        x0, x1 = 0.5 * x, 1.5 * x
        ax.plot([x0, x1], [y, y], 'white', lw=1)
        ax.plot([x0, x0], [y - dy, y + dy], 'white', lw=1)
        ax.plot([x1, x1], [y - dy, y + dy], 'white', lw=1)
        ax.text(0.5 * (x0 + x1), y + dy, t, color='white',
                horizontalalignment='center', fontsize=7)

    # Show requested points
    if points is not None:
        x, y = meters2indices(points[:, 0], points[:, 1])
        ax.plot(
            x, y, 'x', color='#0000ff',
            markeredgewidth=1, markersize=4, alpha=0.3)

    # Show trajectory
    if trajectory is not None:
        x, y = meters2indices(trajectory[:, 0], trajectory[:, 1])
        ax.plot(
            x, y, 'o-', color='#000000',
            lw=0.5, markeredgewidth=0.5, markersize=3)

    # Add labelled points
    if labels:
        n_plotted = 0
        for label, p in labels.items():
            if isinstance(p, nevis.Coords):
                p = p.grid
            x, y = meters2indices(*p)
            if x > 0 and x < nx and y > 0 and y < ny:
                n_plotted += 1
                ax.plot(x, y, 'o', fillstyle='none', label=label)

        if n_plotted:
            ax.legend(
                loc='upper left',
                fontsize=7,
                framealpha=1,
                handlelength=1.0,
                handletextpad=0.6,
            )

    return fig, ax, arr


def save_plot(path, fig, arr):
    """
    Stores the given figure using ``fig.savefig(path)``, but will also check
    that the image dimensions (in pixels) equal the size of ``arr``.

    This check requires ``PIL`` to be installed (will silently fail if not).
    """
    # Store
    fig.savefig(path)

    # Try importing PIL to check image size
    try:
        import PIL
    except ImportError:
        return

    # Suppress "DecompressionBomb" warning
    PIL.Image.MAX_IMAGE_PIXELS = None

    # Open image, get file size
    print(f'Checking size of generated image')
    with PIL.Image.open(path) as im:
        ix, iy = im.size

    if (iy, ix) == arr.shape:
        print('Image size OK')
    else:
        print(f'Unexpected image size: width {ix}, height {iy}')

