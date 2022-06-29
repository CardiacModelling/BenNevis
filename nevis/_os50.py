#!/usr/bin/env python3
"""
Hidden module that provides methods to download, unpack, and process the OS
Terrain 50 data set.
"""
# The zip contains several grid squares, using the lettering described here:
# https://en.wikipedia.org/wiki/Ordnance_Survey_National_Grid
#
# Inspired by
# https://scipython.com/blog/processing-uk-ordnance-survey-terrain-data/
#
import io
import os
import sys
import urllib.request
import zipfile

# Patch the zipfile module to support the PKZIP proprietary DEFLATE64 format
# This is used by two files in the May 2022 release of OS Terrain 50
# (data/sd/sd67_OST50GRID_20220506.zip and data/sd/sd68_OST50GRID_20220506.zip)
import zipfile_deflate64  # noqa

import numpy as np

import nevis


# Base name of the big zip file to read (e.g. to read 'terr50_gagg_gb.zip' we
# put 'terr50_gagg_gb').
terrain_file = 'terr50_gagg_gb'
terrain_file_zip = os.path.join(nevis._DIR_DATA, terrain_file + '.zip')
terrain_file_npy = os.path.join(nevis._DIR_DATA, terrain_file + '.npy')

# URL to download it from
url = ('https://api.os.uk/downloads/v1/products/Terrain50/downloads?'
       'area=GB&format=ASCII+Grid+and+GML+%28Grid%29&redirect')

# Resolution: distance between neighbours in the grid
resolution = 50

# .asc file encoding
ENC = 'utf-8'

# Cached heights
_heights = None


class DataNotFoundError(RuntimeError):
    """ Raised when the OS50 data is not found. """


def spacing():
    """ Returns the spacing between any two grid points. """
    return resolution


def gb(downsampling=None):
    """
    Returns an array of elevation data for Great Britain, with height in meters
    and grid points spaced 50m apart.

    Array indices are (height, width), also known as (northings, eastings).

    A downsampled version can be returned for testing purposes, by setting
    ``downsampling`` to any integer greater than one.
    """
    global _heights

    # Load data (or retrieve from cache)
    if _heights is None:
        # Check file exists
        if not os.path.isfile(terrain_file_npy):
            raise DataNotFoundError(
                f'OS Terrain 50 data not found in {nevis._DIR_DATA}.'
                ' Please use nevis.download_os50() to download and process'
                ' this data set.'
            )

        # Load
        _heights = np.load(terrain_file_npy)
        _heights.setflags(write=False)

    # Return downsampled version for testing (but keep full version in cache)
    if downsampling is not None:
        downsampling = int(downsampling)
        if downsampling > 1:
            return _heights[::downsampling, ::downsampling]

    return _heights


def download_os50(force=False):
    """
    Downloads, unpacks and processes the OS Terrain 50 data set.

    If a previously downloaded zip file is found then the downloading step is
    skipped, unless ``force`` is set to ``True``.

    If a previously unpacked and processed file is found, this method does
    nothing unless ``force`` is set to ``True``.
    """
    global _heights

    # Already done and not forcing? Then return
    if (not force) and os.path.isfile(terrain_file_npy):
        print('Downloaded, unpacked, and processed file already found:'
              ' Skipping.')
        return

    # Check directory exists, show message saying it will be created and how to
    # change its location.
    make_dirs = not os.path.isdir(nevis._DIR_DATA)
    if make_dirs:
        msg = (
            f'This method will create a directory: {nevis._DIR_DATA}\n'
            'This will be used to store the OS Terrain 50 data set in both a'
            ' compressed (160mb) and uncompressed (1.5gb) form, as well as'
            ' additional files that can reach several gb in size.\n'
            'These files will NOT be deleted automatically when nevis is'
            ' uninstalled.\n'
        )
        if nevis._ENV_DATA in os.environ:
            msg += 'This path was'
        else:
            msg += 'An alternative directory can be'
        msg += f' specified with the environment variable: {nevis._ENV_DATA}'
        print(msg)

    # Download zip file
    if force or not os.path.isfile(terrain_file_zip):
        print('The OS Terrain 50 database will be downloaded from')
        print(f'  {url}')
        print()
        yesno = input('Continue? (y/n) ')
        if yesno.lower() not in ['y', 'yes']:
            print('Halted.')
            return

        if make_dirs:
            os.makedirs(nevis._DIR_DATA)
        download_gagg(url, terrain_file_zip)

    # Unpack / process
    if force or not os.path.isfile(terrain_file_npy):

        # Create empty array
        width, height = nevis.dimensions()
        nx, ny = width // resolution, height // resolution
        heights = np.empty((ny, nx), dtype=np.float32)
        heights.fill(np.nan)

        # Fill it up
        extract(terrain_file, heights, resolution)

        # Replace missing values by far-below-sea level
        heights[np.isnan(heights)] = -100

        # Fix odd squares
        fix_sea_levels_in_odd_squares(heights)

        # Add a few fake damns
        save_cambridgeshire(heights)

        # Use "sea mask" to set sea points to -100
        set_sea_level(heights, -100)

        # Make sea slope to make land more findable
        add_sea_slope(heights, -100)

        print(f'Saving to {terrain_file_npy}...')
        np.save(terrain_file_npy, heights)

        # Store
        _heights = heights


def download_gagg(url, fname, print_to_screen=True):
    """
    Downloads the (160mb) ``gagg`` file from Ordnance Survey.
    """
    if print_to_screen:
        print('Downloading terrain data...')
    url = urllib.request.urlopen(url)
    try:
        raw_data = url.read()
    finally:
        url.close()

    if print_to_screen:
        print('Writing...')
    with open(fname, 'wb') as f:
        f.write(raw_data)


def extract(basename, heights, resolution, print_to_screen=True):
    """
    Extracts data from an "ASCII Grid and GML (Grid)" file at ``basename``.zip,
    and extracts the data into numpy array ``heights``.

    The resolution of each file inside the zip must be the same, and must be
    specified as ``resolution``.
    """
    # Open zip file
    if print_to_screen:
        print(f'Reading from {terrain_file_zip}')
        i = 0

    t = nevis.Timer()
    with zipfile.ZipFile(terrain_file_zip, 'r') as f:

        # Find inner zip files
        zips = []
        for name in f.namelist():
            if os.path.splitext(name)[1] == '.zip':
                zips.append(name)
        zips.sort()

        # Read nested zip files
        for name in zips:
            read_nested_zip(f, name, heights, resolution)

            if print_to_screen:
                i += 1
                print('.', end=(None if i % 79 == 0 else ''))
                sys.stdout.flush()

    if print_to_screen:
        print(f'\nFinished, after {t.format()}')


def read_nested_zip(parent, name, heights, resolution):
    """
    Opens a zip-in-a-zip and reads any ``.asc`` files inside it.
    """
    # Open zip-in-a-zip
    with parent.open(name, 'r') as par:
        nested = io.BytesIO(par.read())
        with zipfile.ZipFile(nested) as f:

            # Scan for asc files
            for path in f.namelist():
                if os.path.splitext(path)[1] == '.asc':

                    # Read internal asc
                    with f.open(path, 'r') as asc:
                        try:
                            read_asc(asc, heights, resolution)
                        except Exception as e:
                            raise Exception(
                                f'Error reading {path} in {name}: {str(e)}.')


def read_asc(handle, heights, resolution):
    """
    Extracts data from a handle pointing to an already opened ``.asc`` file.
    """
    # Grab all text in one go and decode
    lines = handle.read().decode(ENC).splitlines()

    # Head lines
    def header(line, field):
        start = field.strip() + ' '
        n = len(start)
        if line[:n] != start:
            raise Exception(
                f'Unexpected header line. Got "{line}", expecting "{start}".')
        return int(line[n:])

    # Ncols and nrows
    ncols = header(lines[0], 'ncols')
    nrows = header(lines[1], 'nrows')

    # Offset
    xll = header(lines[2], 'xllcorner') // resolution
    yll = header(lines[3], 'yllcorner') // resolution

    # Resolution
    cellsize = header(lines[4], 'cellsize')
    if cellsize != resolution:
        raise Exception(
            f'Unexpected resolution. Got {cellsize}, expecting {resolution}.')

    # Optional missing value indicator
    missing = None
    offset = 5
    if lines[offset].startswith('nodata_value '):
        missing = lines[offset].split()[1:2]
        offset += 1

    # Read data
    data = np.genfromtxt(
        lines[offset:],
        delimiter=' ',
        missing_values=missing,
        filling_values=[np.nan],
        max_rows=nrows,
    )
    assert data.shape == (nrows, ncols)

    # Insert data into vector
    heights[yll:yll + nrows, xll:xll + ncols] = data[::-1, :]


def fix_sea_levels_in_odd_squares(heights):
    """
    "Correct" sea level data in squares with known anomalies.
    """
    # Fix sea level in NT68 (last checked on 2022-06-27)
    x, w = nevis.Coords.from_square_with_size('NT68')
    x, y = x.grid[0] // resolution, x.grid[1] // resolution
    w = w // resolution
    view = heights[y:y + w, x:x + w]
    view[view < 2.5] -= 2.1

    # Fix sea level in NR24, 34, 44 (last checked on 2022-06-27)
    x, w = nevis.Coords.from_square_with_size('NR24')
    x, y = x.grid[0] // resolution, x.grid[1] // resolution
    w = w // resolution
    view = heights[y:y + w, x:x + 3 * w]
    view[view < 0.2] -= 10

    # Fix sea level in NR33 (last checked on 2022-06-27)
    x, w = nevis.Coords.from_square_with_size('NR33')
    x, y = x.grid[0] // resolution, x.grid[1] // resolution
    w = w // resolution
    view = heights[y:y + w, x:x + w]
    view[view < 0.2] -= 10

    # Fix sea level in NR35 (last checked on 2022-06-27)
    x, w = nevis.Coords.from_square_with_size('NR35')
    x, y = x.grid[0] // resolution, x.grid[1] // resolution
    w = w // resolution
    view = heights[y:y + w, x:x + w]
    view[view < 0.2] -= 0.5

    # Fix sea level in NR56 (last checked on 2022-06-27)
    x, w = nevis.Coords.from_square_with_size('NR56')
    x, y = x.grid[0] // resolution, x.grid[1] // resolution
    w = w // resolution
    view = heights[y:y + w, x:x + w]
    view[view < 0.1] = -10

    # Fix sea level in NR57 (last checked on 2022-06-27)
    x, w = nevis.Coords.from_square_with_size('NR57')
    x, y = x.grid[0] // resolution, x.grid[1] // resolution
    w = w // resolution
    view = heights[y:y + w, x:x + w]
    view[view < 0.1] -= 0.5

    # Fix sea level in NR76 (last checked on 2022-06-27)
    x, w = nevis.Coords.from_square_with_size('NR76')
    x, y = x.grid[0] // resolution, x.grid[1] // resolution
    w = w // resolution
    view = heights[y:y + w, x:x + w]
    view[view < 0.1] -= 0.5

    # Fix sea level in NR65,75,64,74 (last checked on 2022-06-27)
    x, w = nevis.Coords.from_square_with_size('NR64')
    x, y = x.grid[0] // resolution, x.grid[1] // resolution
    w = w // resolution
    view = heights[y:y + 2 * w, x:x + 2 * w]
    view[view < 0.1] = -10
    del(view)


def save_cambridgeshire(heights):
    """
    Artificially raise the level of some river beds to stop Cambridgeshire from
    flooding.
    """
    # Last checked 2022-06-27

    # Block river in TF 50, stopping a lot of flooding in cambridgeshire
    heights[6047, 11183] = 0.01

    # Block river Yare in TG 50, and Oulton Dyke in TM59, stopping lots of
    # flooding near Norwich
    heights[6151, 13041] = 0.01
    heights[5851, 13013] = 0.01


def set_sea_level(heights, s, print_to_screen=True):
    """
    Create a "mask" on the heights map, by setting all entries suspected to be
    sea to a fixed (very low) "sea level" value ``s``.
    """
    # Find a "sea mask", set all pixels to s
    if print_to_screen:
        print('Creating sea bitmask...')
    t = nevis.Timer()

    # Treat each square separately, starting bottom left and spiraling inwards
    # To iterate in this way, we first create a list of squares
    d = 80  # Trial and error shows this is near optimal
    squares = _spiral_squares(heights, d)

    # The edges are all sea
    e = 1
    heights[:e, :] = s
    heights[-e:, :] = s
    heights[:, :e] = s
    heights[:, -e:] = s

    # Iterate over squares, and apply "sea mask" in each individually
    iters = 0
    ny, nx = heights.shape
    zmax = 100
    for z in range(zmax):

        skip = []
        changed = False
        for i, sq in enumerate(squares):
            if print_to_screen:
                iters += 1
                if iters % 100 == 0:
                    print('.', end=(None if (iters // 100) % 79 == 0 else ''))
                    sys.stdout.flush()

            # Create views of center of square, plus neighbours
            x0, y0 = sq
            x1, y1 = x0 + d, y0 + d

            # At the edge? Then translate by 1 pixel
            x0, y0 = max(x0, 1), max(y0, 1)
            x1, y1 = min(x1, nx - 1), min(y1, ny - 1)

            # Create view and views of neighbours
            v = heights[y0: y1, x0: x1]
            v0 = heights[y0 + 1: y1 + 1, x0: x1]  # Above
            v1 = heights[y0 - 1: y1 - 1, x0: x1]  # Below
            v2 = heights[y0: y1, x0 - 1: x1 - 1]  # Left
            v3 = heights[y0: y1, x0 + 1: x1 + 1]  # Right

            # Skip easy squares
            if np.all(v < 0):
                if (np.any(v == s) | np.any(v0 == s) | np.any(v1 == s)
                        | np.any(v2 == s) | np.any(v3 == s)):
                    v[:] = s
                    skip.append(i)
                    changed = True
                    # Don't skip if < 0 but no s neighbours _yet_
                continue
            elif np.all(v > 0):
                skip.append(i)
                continue

            kmax = 1000
            for k in range(1000):
                n = (v <= 0) & (v != s) & (
                    (v0 == s) | (v1 == s) | (v2 == s) | (v3 == s))
                if not np.any(n):
                    break
                v[n] = s
                changed = True
            if k + 1 == kmax:
                print('WARNING: Reached kmax')

        for i in reversed(skip):
            del(squares[i])
        if not squares:
            break
        if not changed:
            break

    if z + 1 == zmax:
        print('WARNING: Reached zmax')

    if print_to_screen:
        print(f'\nFinished, after {t.format()}')


def add_sea_slope(heights, s, print_to_screen=True):
    """
    Make the sea slope downwards, as you move further away from the coast.
    """
    print('Adding slope to sea bed')
    t = nevis.Timer()

    h = 0.01
    ny, nx = heights.shape

    v0 = heights[1:]
    v1 = heights[:-1]
    v2 = heights[:, 1:]
    v3 = heights[:, :-1]

    yd, xd = np.nonzero(np.logical_and(v1 == s, v0 != s))
    yu, xu = np.nonzero(np.logical_and(v0 == s, v1 != s))
    yl, xl = np.nonzero(np.logical_and(v3 == s, v2 != s))
    yr, xr = np.nonzero(np.logical_and(v2 == s, v3 != s))
    y = np.concatenate((yd, yu + 1, yl, yr))
    x = np.concatenate((xd, xu, xl, xr + 1))
    heights[y, x] = s - h

    j = 0
    for i in range(ny * nx):
        div = 1 if len(x) > 300000 else (10 if len(x) > 50000 else 100)
        if i % div == 0:
            j += 1
            print('.', end=(None if j % 79 == 0 else ''))
            sys.stdout.flush()

        # Move down
        ok = np.nonzero(y > 0)
        yd, xd = y[ok] - 1, x[ok]
        ok = np.nonzero((heights[yd, xd] == s)
                        | (heights[yd, xd] < heights[yd + 1, xd] - h))
        yd, xd = yd[ok], xd[ok]
        heights[yd, xd] = heights[yd + 1, xd] - h

        # Move up
        ok = np.nonzero(y < ny - 1)
        yu, xu = y[ok] + 1, x[ok]
        ok = np.nonzero((heights[yu, xu] == s)
                        | (heights[yu, xu] < heights[yu - 1, xu] - h))
        yu, xu = yu[ok], xu[ok]
        heights[yu, xu] = heights[yu - 1, xu] - h

        # Move left
        ok = np.nonzero(x > 0)
        yl, xl = y[ok], x[ok] - 1
        ok = np.nonzero((heights[yl, xl] == s)
                        | (heights[yl, xl] < heights[yl, xl + 1] - h))
        yl, xl = yl[ok], xl[ok]
        heights[yl, xl] = heights[yl, xl + 1] - h

        # Move right
        ok = np.nonzero(x < nx - 1)
        yr, xr = y[ok], x[ok] + 1
        ok = np.nonzero((heights[yr, xr] == s)
                        | (heights[yr, xr] < heights[yr, xr - 1] - h))
        yr, xr = yr[ok], xr[ok]
        heights[yr, xr] = heights[yr, xr - 1] - h

        y = np.concatenate((yd, yu, yl, yr))
        x = np.concatenate((xd, xu, xl, xr))

        if len(y) == 0:
            break

    heights[heights < s] -= s

    print(f'\nFinished, after {t.format()}')


def _spiral_squares(heights, d):
    """
    Returns a list of squares (indicated by the lower-left corner) that cover
    the map, starting lower-left and spiraling inward. Each square has size
    ``d``.
    """
    squares = []
    x0, y0 = (0, 0)
    y1, x1 = heights.shape
    while x1 > x0:
        for x in range(x0, x1, d):
            squares.append((x, y0))
        y0 += d
        if y1 <= y0:
            break
        for y in range(y0, y1, d):
            squares.append((x1 - d, y))
        x1 -= d
        if x1 <= x0:
            break
        for x in range(x1 - d, x0 - d, -d):
            squares.append((x, y1 - d))
        y1 -= d
        if y1 <= y0:
            break
        for y in range(y1 - d, y0 - d, -d):
            squares.append((x0, y))
        x0 += d
    return squares
