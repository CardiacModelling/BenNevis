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
import os
import tempfile
import warnings

import matplotlib.colors
import matplotlib.figure
import numpy as np

import nevis


def plot(boundaries=None, labels=None, trajectory=None, points=None,
         scale_bar=True, big_grid=False, small_grid=False, downsampling=27,
         silent=True, headless=True):
    """
    Creates a plot of the 2D elevation data in ``heights``, downsampled with a
    factor ``downsampling``.

    Note that this method assumes you will want to write the figure to disk
    with :meth:`fig.savefig()`. If you want to display it using ``pyplot``,
    set ``headless=False``.

    Arguments:

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
    ``big_grid``
        Show the 2-letter grid squares (100km by 100km).
    ``small_grid``
        Show the 2-letter 2-number grid squares (10km by 10km)
    ``downsampling``
        Set to any integer to set the amount of downsampling (the ratio of data
        points to pixels in either direction).
    ``silent``
        Set to ``True`` to stop writing a status to stdout.
    ``headless``
        Set to ``False`` to create the figure using pyplot.

    Returns a tuple ``(fig, ax, heights, g)`` where ``fig`` is the created
    figure, ``ax`` is the axes the image is plotted on, and ``heights`` is the
    downsampled numpy array. The final entry ``g`` is a function that converts
    coordinates in meters to coordinates on the map axes.
    """
    # Current array shape
    heights = nevis.gb()
    ny, nx = heights.shape

    # Get extreme points (before any downsampling!)
    vmin = np.min(heights)
    vmax = np.max(heights)
    if not silent:
        print(f'Lowest point: {vmin}')
        print(f'Highest point: {vmax}')

    # Downsample (27 gives me a map that fits on my screen at 100% zoom).
    if downsampling > 1:
        if not silent:
            print(f'Downsampling with factor {downsampling}')
        heights = heights[::downsampling, ::downsampling]
        ny, nx = heights.shape

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
        heights = heights[ylo:yhi, xlo:xhi]

        # Adjust array size
        ny, nx = heights.shape

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
            (0, '#4872d3'),             # Deep sea blue
            (f(-0.1), '#68b2e3'),       # Shallow sea blue
            (f(0.0), '#0f561e'),        # Dark green
            (f(10), '#1a8b33'),         # Nicer green
            (f(100), '#11aa15'),        # Glorious green
            (f(300), '#e8e374'),        # Yellow at ~1000ft
            (f(610), '#8a4121'),        # Brownish at ~2000ft
            (f(915), '#999999'),        # Grey at ~3000ft
            (1, 'white'),
        ], N=1024)
    #import matplotlib.cm
    #cmap = matplotlib.cm.get_cmap('inferno')

    # Work out figure dimensions
    # Note: Matplotlib defaults to 100 dots per inch and 72 points per inch for
    # font sizes and line widths. This means that increasing the dpi leads to
    # more pixels per inch, but also to much bigger letters and thicker lines,
    # as it assumes the physical size should stay the same when printed!
    dpi = 100
    fw = nx / dpi
    fh = ny / dpi
    if not silent:
        print(f'Figure dimensions: {fw}" by {fh}" at {dpi} dpi')
        print(f'Should result in {nx} by {ny} pixels.')

    # Create figure
    if headless:
        fig = matplotlib.figure.Figure(figsize=(fw, fh), dpi=dpi)
    else:
        import matplotlib.pyplot as plt
        fig = plt.figure(figsize=(fw, fh), dpi=dpi)
    fig.subplots_adjust(0, 0, 1, 1)

    # Add axes
    ax = fig.add_subplot(1, 1, 1)
    ax.set_axis_off()
    ax.imshow(
        heights,
        origin='lower',
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
        interpolation='none',
    )
    ax.set_xlim(0, nx)
    ax.set_ylim(0, ny)

    # Add grid
    if small_grid:
        for sq, x0, y0 in nevis.squares():
            for j in range(10):
                for i in range(10):
                    x, y = x0 + j * 10000, y0 + i * 10000
                    if y == 0 and x > 0:
                        q, r = meters2indices(x, y)
                        if q > 2 and q < nx - 2:
                            ax.axvline(q, color='w', lw=0.5)
                    elif x == 0 and y > 0:
                        q, r = meters2indices(x, y)
                        if r > 2 and r < ny - 2:
                            ax.axhline(r, color='w', lw=0.5)
                    q, r = meters2indices(x + 5000, y + 5000)
                    if q > 20 and q < nx - 20 and r > 10 and r < ny - 10:
                        ax.text(q, r, sq + str(j) + str(i), color='w',
                                ha='center', va='center', fontsize=10)
    elif big_grid:
        for sq, x, y in nevis.squares():
            if y == 0 and x > 0:
                q, r = meters2indices(x, y)
                if q > 0 and q < nx:
                    ax.axvline(q, color='w', lw=0.5)
            elif x == 0 and y > 0:
                q, r = meters2indices(x, y)
                if r > 0 and r < ny:
                    ax.axhline(r, color='w', lw=0.5)
            q, r = meters2indices(x + 50000, y + 50000)
            if q > 20 and q < nx - 20 and r > 10 and r < ny - 10:
                ax.text(q, r, sq, color='w',
                        ha='center', va='center', fontsize=14)

    # Add scale bar
    if scale_bar:
        # Guess a good size
        x = d_new[0] / 5
        if x > 250e3:
            x = int(round(x / 250e3) * 250e3)
        elif x > 90e3:
            x = int(round(x / 100e3) * 100e3)
        elif x > 9e3:
            x = int(round(x / 10e3) * 10e3)
        elif x > 4.5e3:
            x = int(round(x / 5e3) * 5e3)
        elif x > 1e3:
            x = int(round(x / 1e3) * 1e3)
        else:
            x = int(round(x / 100) * 100)
        t = f'{x}m' if x < 1000 else f'{x // 1000}km'
        x = x / d_new[0] * nx
        y = 0.05 * ny
        dy = 0.015 * ny
        x0, x1 = 0.5 * x, 1.5 * x
        ax.plot([x0, x1], [y, y], 'white', lw=1)
        ax.plot([x0, x0], [y - dy, y + dy], 'white', lw=1)
        ax.plot([x1, x1], [y - dy, y + dy], 'white', lw=1)
        ax.text(0.5 * (x0 + x1), y + 0.5 * dy, t, color='white',
                horizontalalignment='center')

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
            lw=0.5, markeredgewidth=0.5, markersize=4)

    # Add labelled points
    if labels:
        n_plotted = 0
        kwargs = {'fillstyle': 'none', 'markersize': 12}
        for label, p in labels.items():
            if isinstance(p, nevis.Coords):
                p = p.grid
            x, y = meters2indices(*p)
            if x > 0 and x < nx and y > 0 and y < ny:
                n_plotted += 1
                ax.plot(x, y, 'wo', markeredgewidth=3, **kwargs)
                ax.plot(x, y, 'o', markeredgewidth=2, label=label, **kwargs)

        if n_plotted:
            ax.legend(
                loc='upper left',
                framealpha=1,
                handlelength=1.5,
                handletextpad=0.9,
            )

    return fig, ax, heights, meters2indices


def plot_line(f, point_1, point_2, label_1='Point 1', label_2='Point 2',
              padding=0.25, evaluations=400, figsize=(8, 5), headless=True):
    """
    Draws a line between two points and evaluates a function along it.

    Note that this method assumes you will want to write the figure to disk
    with :meth:`fig.savefig()`. If you want to display it using ``pyplot``,
    set ``headless=False``.

    Arguments:

    ``f``
        A function ``f(x, y) -> z``, or a sequence of multiple such functions.
    ``point_1``
        The first point as a set of Coords or a numpy array in meters.
    ``point_2``
        The second point.
    ``label_1``, ``label_2``
        Optional labels for the points.
    ``padding``
        The amount of padding shown to the left and right of the points, as a
        fraction of the total line length (e.g. ``padding=0.25`` extends the
        line on either side by 25% of the distance between the two points).
    ``evaluations``
        The number of evaluations of ``f`` to plot.
    ``figsize``
        The default figure size
    ``headless``
        Set to ``False`` to create the figure using pyplot.

    Returns a tuple ``(fig, ax, p1, p2)`` where ``fig`` is the generated
    figure, ``ax`` is the axes object within that figure, and ``p1`` and ``p2``
    are the extremities of the line (points 1 and 2 plus padding) (as Coords).
    """
    # Points as vectors
    if isinstance(point_1, nevis.Coords):
        point_1 = point_1.grid
    if isinstance(point_2, nevis.Coords):
        point_2 = point_2.grid

    # Direction vector
    r = point_2 - point_1
    d = np.sqrt(r[0]**2 + r[1]**2)

    # Points to evaluate
    s = np.linspace(-padding, 1 + padding, evaluations)
    p = [point_1 + sj * r for sj in s]

    # Functions
    if callable(f):
        fs = [f]
    else:
        fs = f
        for f in fs:
            if not callable(f):
                raise ValueError(
                    'f must be a callable or a sequence of callables.')

    # Evaluations-es
    ys = [[f(*x) for x in p] for f in fs]

    # Create figure
    if headless:
        fig = matplotlib.figure.Figure(figsize=figsize)
    else:
        import matplotlib.pyplot as plt
        fig = plt.figure(figsize=figsize)

    # Plot
    fig.subplots_adjust(0.1, 0.1, 0.99, 0.99)
    ax = fig.add_subplot(1, 1, 1)
    ax.set_xlabel('Distance (m)')
    ax.set_ylabel('Altitude - according to our interpolation (m)')
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    for k, y in enumerate(ys):
        ax.plot(s * d, y, label=f'Function {1 + k}')
    ax.axvline(0, ls='-', color='r', label=label_1)
    ax.axvline(d, ls='--', color='k', label=label_2)
    ax.axvspan(0, d, color='#fffede', lw=0, zorder=-1)
    ax.legend()

    return fig, ax, nevis.Coords(*p[0]), nevis.Coords(*p[-1])


def save_plot(path, fig, heights=None, silent=True):
    """
    Stores the given figure using ``fig.savefig(path)``.

    If ``heights`` is given and ``PIL`` (pillow) is installed it will also
    check that the image dimensions (in pixels) equal the size of ``heights``.
    """
    if not silent:
        print(f'Writing figure to {path}')
    fig.savefig(path)

    # Try importing PIL to check image size
    if heights is None:
        return
    try:
        import PIL
    except ImportError:
        return

    # Suppress "DecompressionBomb" warning
    PIL.Image.MAX_IMAGE_PIXELS = None

    # Open image, get file size
    if not silent:
        print('Checking size of generated image')
    with PIL.Image.open(path) as im:
        ix, iy = im.size

    if (iy, ix) == heights.shape:
        if not silent:
            print('Image size OK')
    else:
        warnings.warn(
            f'Unexpected image size: width {ix}, height {iy}, expecting'
            f' {heights.shape}.')


def png_bytes(fig):
    """
    Converts a matplotlib figure to a ``bytes`` string containing its ``.PNG``
    representation.
    """
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, 'result.png')
        fig.savefig(path)
        del(fig)
        with open(path, 'rb') as f:
            return f.read()

