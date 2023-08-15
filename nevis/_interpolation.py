#!/usr/bin/env python3
"""
Module providing interpolation methods over the OS 50 data set.
"""
import os
import pickle

import numpy as np
import scipy.interpolate

import nevis


class linear_interpolant(object):
    """
    Returns a linear interpolation and optionally its gradient over the full
    GB data set.

    When ``grad`` is set to ``False`` (by default), the returned function
    takes two arguments ``x`` and ``y`` (both in metres) and returns an
    interpolated height ``z`` (in meters).

    When ``grad`` is set to ``True``, the returned function takes two
    arguments ``x`` and ``y`` (both in metres) and returns a tuple ``(z, g)``,
    where ``z`` is an interpolated height (in meters) and ``g`` is a tuple
    ``(dz/dx, dz/dy)``.

    The height for each grid point ``(i, j)`` is assumed to be in the center of
    the square from ``(i, j)`` to ``(i + 1, j + 1)``.

    Example::

        f = linear_interpolation()
        print(f(1000, 500))

        f_grad = linear_interpolation(grad=True)
        z, (gx, gy) = f_grad(1000, 500)
        print(f"Height: {z:.2f} m, gradient: ({gx:.2f} m/m, {gy:.2f} m/m)")

    """
    # Note: This is technically a class, but used as a function here so
    # following the underscore naming convention.

    def __init__(self, grad=False):
        self._heights = nevis.gb()
        self._resolution = nevis.spacing()
        self._grad = grad

    def __call__(self, x, y):
        ny, nx = self._heights.shape
        x, y = x / self._resolution - 0.5, y / self._resolution - 0.5

        # Find nearest grid points
        # x1 (left), x2 (right), y1 (bottom), y2 (top).

        # Nearest grid points
        # When outside the grid, we use the _two_ points nearest the edge
        # (resulting in an extrapolation)
        x1 = np.minimum(nx - 2, np.maximum(0, int(x)))
        y1 = np.minimum(ny - 2, np.maximum(0, int(y)))
        x2 = x1 + 1
        y2 = y1 + 1

        # Heights at nearest grid points (subscripts are x_y)
        h11 = self._heights[y1, x1]
        h12 = self._heights[y2, x1]
        h21 = self._heights[y1, x2]
        h22 = self._heights[y2, x2]

        # We omit the 1 / (x2 - x1) and 1 / (y2 - y1) terms as these are always
        # 1 in the normal (interpolating) case.
        # When extrapolating, we get e.g. x1 == x2, so that
        # (x2 - x) == (x1 - x)

        # X-direction interpolation on both y values
        f1 = np.where(h11 == h21, h11, (x2 - x) * h11 + (x - x1) * h21)
        f2 = np.where(h12 == h22, h12, (x2 - x) * h12 + (x - x1) * h22)

        # Final result
        f = float(np.where(f1 == f2, f1, (y2 - y) * f1 + (y - y1) * f2))
        if self._grad:
            # Gradient of the interpolant
            g = (h21 - h11) / self._resolution, (h12 - h11) / self._resolution
            return f, g
        else:
            return f


def spline(verbose=False):
    """
    Returns a spline interpolation over the full GB data set.

    The returned function takes two arguments ``x`` and ``y`` (both in metres)
    and returns an interpolated height ``z`` (in meters).

    Example::

        f = spline()
        print(f(1000, 500))

    Notice: Calling this method will result in the creation and storage of a
    very large cache file in the nevis data directory.
    """
    heights = nevis.gb()

    # Load pickled spline
    s = None
    cached = os.path.join(nevis._DIR_DATA, 'spline')
    if os.path.isfile(cached):
        if verbose:
            print('Loading cached spline...')
        try:
            with open(cached, 'rb') as f:
                s = pickle.load(f)
        except Exception:
            if verbose:
                print('Loading failed.')

    # Create new spline
    if s is None:
        if verbose:
            print('Reticulating splines...')
        width, height = nevis.dimensions()
        ny, nx = heights.shape
        c = 25  # Correction: Coords at lower-left, height is center of square
        t = nevis.Timer()
        s = scipy.interpolate.RectBivariateSpline(
            np.linspace(0, height, ny, endpoint=False) + c,
            np.linspace(0, width, nx, endpoint=False) + c,
            heights,
        )
        if verbose:
            print(f'Completed in {t.format()}')

        # Cache to disk
        if verbose:
            print('Caching spline to disk...')
            t = nevis.Timer()
        with open(cached, 'wb') as f:
            pickle.dump(s, f)
        if verbose:
            print(f'Completed in {t.format()}')

    return lambda x, y: s(y, x)[0][0]
