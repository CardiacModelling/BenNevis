#!/usr/bin/env python3
"""
Provides the method :meth:`data.gb()` that returns elevation data for Great
Brittain, obtained from the Ordnance Survey data set ``terr50_gagg_gb``.
"""
# The zip contains several grid squares, using the lettering described here:
# https://en.wikipedia.org/wiki/Ordnance_Survey_National_Grid
#
# Inspired by
# https://scipython.com/blog/processing-uk-ordnance-survey-terrain-data/
#
import csv
import io
import os
import pickle
import random
import sys
import urllib.request
import zipfile

# Patch the zipfile module to support the PKZIP proprietary DEFLATE64 format
# This is used by two files in the May 2022 release of OS Terrain 50
# (data/sd/sd67_OST50GRID_20220506.zip and data/sd/sd68_OST50GRID_20220506.zip)
import zipfile_deflate64  # noqa

import numpy as np
import scipy.interpolate
import scipy.spatial
import bnglonlat

import nevis

# Get accurate longitude/lattitude, or use fallback
try:
    import convertbng.util

    def lonlat(x, y):
        a, b = convertbng.util.convert_lonlat([x], [y])
        if not (np.isnan(a) or np.isnan(b)):
            return a[0], b[0]
        return bnglonlat.bnglonlat(x, y)

except ImportError:
    lonlat = bnglonlat.bnglonlat


# Data directory
data = 'data'

# Base name of the big zip file to read (e.g. to read 'terr50_gagg_gb.zip' we
# put 'terr50_gagg_gb').
terrain_file = 'terr50_gagg_gb'

# URL to download it from
url = ('https://api.os.uk/downloads/v1/products/Terrain50/downloads?'
       'area=GB&format=ASCII+Grid+and+GML+%28Grid%29&redirect')

# Resolution: distance between neighbours in the grid
resolution = 50

# Full size of the grid to construct (in meters)
# For 'terr50_gagg_gb' we're assuming 700km by 1300km
# Origin is a bottom left (in SV square)
width, height = 700000, 1300000

# .asc file encoding
ENC = 'utf-8'

# Hill names
hill_zip = os.path.join(data, 'hills.zip')
hill_file = 'hills.csv'

# Grid letters (bottom to top, left to right)
GL = [
    ['V', 'W', 'X', 'Y', 'Z'],
    ['Q', 'R', 'S', 'T', 'U'],
    ['L', 'M', 'N', 'O', 'P'],
    ['F', 'G', 'H', 'J', 'K'],
    ['A', 'B', 'C', 'D', 'E'],
]

# Cached heights
_heights = None


def download(url, fname):
    """
    Downloads the (160mb) gagg file from Ordnance Survey.
    """
    fname = os.path.join(data, fname)
    if os.path.isfile(fname):
        return

    print(f'File {fname} not found.')
    print(f'Will attempt to download from {url[:40]}...')
    yesno = input('Is that OK? (y/n) ')
    if yesno.lower() not in ['y', 'yes']:
        print('Aborting...')
        sys.exit(1)

    print('Downloading terrain data...')
    url = urllib.request.urlopen(url)
    try:
        raw_data = url.read()
    finally:
        url.close()

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
    fname = os.path.join(data, f'{basename}.zip')

    # Open zip file
    if print_to_screen:
        print(f'Reading from {fname}')
        i = 0

    t = nevis.Timer()
    with zipfile.ZipFile(fname, 'r') as f:

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


def gb(downsampling=None):
    """
    Returns an array of elevation data for Great Brittain, with height in
    meters and grid points spaced 50m apart.

    Array indices are (height, width) i.e. (longitude, latitude).

    If required, the data is first downloaded (approx 160MB) and unpacked
    (approx 1.5GB).
    """
    global _heights
    if _heights is None:

        # Read data or cached data
        nx, ny = width // resolution, height // resolution
        cached = os.path.join(data, terrain_file + '.npy')
        if os.path.isfile(cached):
            print('Loading terrain data...')
            heights = np.load(cached)
        else:
            # Ensure zip is downloaded
            download(url, f'{terrain_file}.zip')

            # Create empty array
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

            print(f'Saving to {cached}...')
            np.save(cached, heights)

        # Store
        _heights = heights

        # Downsample a lot, for testing
        if downsampling is not None and downsampling > 1:
            print(f'Downsampling with factor {downsampling}')
            heights = heights[::downsampling, ::downsampling]

    # Check downsampling isn't requested with other ratio
    # (Requests that don't specify are fine!)
    if downsampling is not None and downsampling > 1:
        if downsampling != nevis._heights_downsampling:
            raise ValueError(
                'Data already downsampled with {nevis._heights_downsampling}.')

    return _heights


def fix_sea_levels_in_odd_squares(heights):
    """
    "Correct" sea level data in squares with known anomalies.
    """
    # Fix sea level in NT68 (last checked on 2022-06-27)
    x, w = Coords.from_square_with_size('NT68')
    x, y = x.grid[0] // resolution, x.grid[1] // resolution
    w = w // resolution
    view = heights[y:y + w, x:x + w]
    view[view < 2.5] -= 2.1

    # Fix sea level in NR24, 34, 44 (last checked on 2022-06-27)
    x, w = Coords.from_square_with_size('NR24')
    x, y = x.grid[0] // resolution, x.grid[1] // resolution
    w = w // resolution
    view = heights[y:y + w, x:x + 3 * w]
    view[view < 0.2] -= 10

    # Fix sea level in NR33 (last checked on 2022-06-27)
    x, w = Coords.from_square_with_size('NR33')
    x, y = x.grid[0] // resolution, x.grid[1] // resolution
    w = w // resolution
    view = heights[y:y + w, x:x + w]
    view[view < 0.2] -= 10

    # Fix sea level in NR35 (last checked on 2022-06-27)
    x, w = Coords.from_square_with_size('NR35')
    x, y = x.grid[0] // resolution, x.grid[1] // resolution
    w = w // resolution
    view = heights[y:y + w, x:x + w]
    view[view < 0.2] -= 0.5

    # Fix sea level in NR56 (last checked on 2022-06-27)
    x, w = Coords.from_square_with_size('NR56')
    x, y = x.grid[0] // resolution, x.grid[1] // resolution
    w = w // resolution
    view = heights[y:y + w, x:x + w]
    view[view < 0.1] = -10

    # Fix sea level in NR57 (last checked on 2022-06-27)
    x, w = Coords.from_square_with_size('NR57')
    x, y = x.grid[0] // resolution, x.grid[1] // resolution
    w = w // resolution
    view = heights[y:y + w, x:x + w]
    view[view < 0.1] -= 0.5

    # Fix sea level in NR76 (last checked on 2022-06-27)
    x, w = Coords.from_square_with_size('NR76')
    x, y = x.grid[0] // resolution, x.grid[1] // resolution
    w = w // resolution
    view = heights[y:y + w, x:x + w]
    view[view < 0.1] -= 0.5

    # Fix sea level in NR65,75,64,74 (last checked on 2022-06-27)
    x, w = Coords.from_square_with_size('NR64')
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


def spline():
    """
    Create a spline interpolating over the array of heights.
    """
    heights = gb()

    s = None
    cached = os.path.join(data, 'spline')
    use_cache = '-debug' not in sys.argv
    if use_cache and os.path.isfile(cached):
        print('Unpickling spline...')
        try:
            with open(cached, 'rb') as f:
                s = pickle.load(f)
        except Exception:
            print('Unpickling failed.')

    if s is None:
        print('Reticulating splines...')
        ny, nx = heights.shape
        c = 25  # Correction: Coords at lower-left, height is center of square
        t = nevis.Timer()
        s = scipy.interpolate.RectBivariateSpline(
            np.linspace(0, height, ny, endpoint=False) + c,
            np.linspace(0, width, nx, endpoint=False) + c,
            heights,
        )
        print(f'Completed in {t.format()}')

        if use_cache:
            print('Pickling spline...')
            t = nevis.Timer()
            with open(cached, 'wb') as f:
                pickle.dump(s, f)
            print(f'Completed in {t.format()}')

    return lambda x, y: s(y, x)[0][0]


class Coords(object):
    """
    Coordinates, either normalised (so that 0, 0 is the bottom left of the grid
    and 1, 1 is the top right) or as OS36GB grid points in meters.

    Examples::

        p = nevis.Coords(gridx=123456, gridy=123456)
        print(p.grid)
        print(p.normalised)

        p = nevis.Coords(normx=0.5, normy=0.2)
        print(p.grid)
        print(p.normalised)

        b = nevis.ben()
        print(b.square)
        print(b.geograph)

    """
    def __init__(self, gridx=None, gridy=None, normx=None, normy=None):
        self._gridx = self._gridy = None
        self._normx = self._normy = None

        if gridx is not None and gridy is not None:
            if normx is None and normy is None:
                self._gridx = int(gridx)
                self._gridy = int(gridy)
                self._normx = self._gridx / width
                self._normy = self._gridy / height
        if normx is not None and normy is not None:
            if gridx is None and gridy is None:
                self._normx = float(normx)
                self._normy = float(normy)
                self._gridx = int(self._normx * width)
                self._gridy = int(self._normy * height)
        if self._gridx is None:
            raise ValueError(
                'Either (gridx and gridy) or (normx and normy) must be'
                'specified (and not both).')

        self._latlong = None
        self._square = None
        self._square3 = None
        self._square4 = None
        self._square5 = None

    def _find_square(self, n):

        # Get letters and remaining x y
        if self._square is None:
            # Lower-left of "V" (the bottom-left major letter) is 1000km to the
            # left of the origins of the grid (SV) and 500km below it.
            x, y = self._gridx + 1000000, self._gridy + 500000

            # Get first letter
            a, b = int(y // 500000), int(x // 500000)
            try:
                if a < 0 or b < 0:
                    raise KeyError
                name = GL[a][b]

                # Get second letter
                x, y = x % 500000, y % 500000
                a, b = int(y // 100000), int(x // 100000)
                name += GL[a][b]

                # Get numbers
                x, y = x % 100000, y % 100000
                x, y = int(x), int(y)

                # Make string
                self._square = name, f'{x:0>5}', f'{y:0>5}'
            except KeyError:
                self._square = False

        # Make string
        if self._square is False:
            return 'Off the grid'

        name, x, y = self._square
        return name + x[:n] + y[:n]

    @staticmethod
    def from_square(square):
        """
        Creates coordinates corresponding to the lower-left corner of a grid
        square indicated by letters and numbers, e.g. ``NN166712`` or
        ``NN 166 712``.
        """
        return Coords.from_square_with_size(square)[0]

    @staticmethod
    def from_square_with_size(square):
        """
        Like :meth:`from_square` but returns a tuple ``(coords, size)`` where
        ``size`` is the length of the square's sides.
        """
        code = square.strip().upper()
        if len(code) < 1:
            raise ValueError(
                'Invalid BNG grid reference: must be at least 1 letter')

        def find(letter):
            """
            Find lower-left coordinates. Big squares are 500km, small 100km.
            """
            for i, row in enumerate(GL):
                if letter >= row[0] and letter != 'I':
                    return i, row.index(letter)
            raise ValueError(
                f'Invalid BNG grid letter "{letter}" in code "{square}".')

        # Origin of letter system is V, BNG starts at S
        x, y = -1000000, -500000

        # Process letters
        i, j = find(code[0])
        x, y = x + 500000 * j, y + 500000 * i
        if len(code) == 1:
            return Coords(x, y), 500000

        i, j = find(code[1])
        x, y = x + 100000 * j, y + 100000 * i
        if len(code) == 2:
            return Coords(x, y), 100000

        # Check numbers
        numbers = code[2:].split(maxsplit=1)
        if len(numbers) == 1:
            numbers = numbers[0]
            n = len(numbers)
            if n % 2 == 1:
                raise ValueError(
                    f'Invalid BNG grid code: {square} numbers must have same'
                    ' number of digits.')
            n = n // 2
            numbers = (numbers[:n], numbers[n:])
        else:
            n = max(len(numbers[0]), len(numbers[1]))

        try:
            a, b = int(numbers[0]), int(numbers[1])
        except ValueError:
            raise ValueError(
                f'Invalid BNG grid code: {square} numbers must be integers.')
        if a < 0 or b < 0:
            raise ValueError(
                f'Invalid BNG grid code: {square} numbers must be positive.')

        # Calculate square size
        m = 10**(5 - n)

        # Final grid coordinates
        x, y = x + a * m, y + b * m

        # Pretty much always, we'll want to round
        if m >= 1:
            x, y = int(x), int(y)

        return Coords(x, y), m

    @property
    def grid(self):
        return np.array([self._gridx, self._gridy])

    @property
    def normalised(self):
        return np.array([self._normx, self._normy])

    @property
    def square3(self):
        if self._square3 is None:
            self._square3 = self._find_square(3)
        return self._square3

    @property
    def square4(self):
        if self._square4 is None:
            self._square4 = self._find_square(4)
        return self._square4

    @property
    def square5(self):
        if self._square5 is None:
            self._square5 = self._find_square(5)
        return self._square5

    @property
    def latlong(self):
        if self._latlong is None:
            lon, lat = lonlat(self._gridx, self._gridy)
            self._latlong = lat, lon
        return self._latlong

    @property
    def geograph(self):
        return f'http://www.geograph.org.uk/gridref/{self.square5}'

    @property
    def google(self):
        lat, long = self.latlong
        lat, long = round(lat, 6), round(long, 6)
        return (
            'https://www.google.com/maps/@?api=1&map_action=map'
            f'&center={lat},{long}&zoom=15&basemap=terrain')

    @property
    def osmaps(self):
        lat, long = self.latlong
        lat, long = round(lat, 6), round(long, 6)
        return (
            f'https://explore.osmaps.com/en/pin?lat={lat}&lon={long}&zoom=17')

    @property
    def opentopomap(self):
        lat, long = self.latlong
        lat, long = round(lat, 6), round(long, 6)
        return f'https://opentopomap.org/#marker=15/{lat}/{long}'

    def __str__(self):
        return f'Coords({int(round(self._gridx))}, {int(round(self._gridy))})'


def dimensions():
    """ Returns the dimensions of the grid (width, height) in meters. """
    return width, height


def spacing():
    """ Returns the spacing between any two grid points. """
    return resolution


Coords.ben = Coords(gridx=216666, gridy=771288)
Coords.fen = Coords(gridx=520483, gridy=289083)
Coords.pub = {
    #'Ye olde trip to jerusalem': Coords(gridx=457034, gridy=339443},
    'Bear': Coords(gridx=451473, gridy=206135),
    'Canal house': Coords(gridx=457307, gridy=339326),
    'MacSorleys': Coords(gridx=258809, gridy=665079),
    'Sheffield tap': Coords(gridx=435847, gridy=387030),
}


def ben():
    """ Returns the coordinates of Ben Nevis. """
    return Coords.ben


def fen():
    """ Returns the coordinates of Holme Fen """
    return Coords.fen


def pub(name=None):
    """ Returns coordinates where a mathematician may be found. """
    if name:
        return Coords.pub[name]
    return random.choice(list(Coords.pub.values()))


class Hill(object):
    """
    Known hill tops.

    Examples::

        print(Hill.by_name('Ben Nevis'))
        print(Hill.by_rank(1))
        print(Hill.by_rank(2))
        print(Hill.by_rank(3))

        h, d = Hill.nearest(Coords(gridx=216600, gridy=771300))
        print(h)

    """
    _hills = []
    _names = {}
    _ids = {}
    _tree = None

    def __init__(self, x, y, rank, height, hill_id, name):
        if Hill._tree is not None:
            raise ValueError('Cannot add hills after tree construction.')
        self._x = int(x)
        self._y = int(y)
        self._rank = int(rank)
        self._height = float(height)
        self._id = int(hill_id)
        self._name = name.strip()
        self._photo = None
        Hill._hills.append(self)
        Hill._names[self._name.lower()] = self
        Hill._ids[self._id] = self

    @staticmethod
    def _load():
        """ Loads hills into memory. """

        # Unzip
        with zipfile.ZipFile(hill_zip, 'r') as f:
            with f.open(hill_file, 'r') as g:
                lines = g.read().decode('utf-8')
        lines = lines.splitlines()
        rows = iter(csv.reader(lines, delimiter=',', quotechar='"'))

        # Parse header
        fields = ['x', 'y', 'rank', 'meters', 'id', 'name']
        header = next(rows)
        try:
            indices = [header.index(field) for field in fields]
        except ValueError as e:
            raise ValueError(f'Unable to read hill-file header: {e}')

        # Parse data
        coords = []
        for row in rows:
            Hill(*[row[i] for i in indices])
            coords.append([row[indices[0]], row[indices[1]]])

        # Construct tree
        Hill._tree = scipy.spatial.KDTree(np.array(coords, dtype=np.float32))

    @staticmethod
    def by_id(hill_id):
        """
        Return a hill with the given ``hill_id`` (as used on e.g. hill
        bagging.)
        """
        if not Hill._hills:
            Hill._load()
        return Hill._ids[hill_id]

    @staticmethod
    def by_name(name):
        """ Return a hill with the given ``name``. """
        if not Hill._hills:
            Hill._load()
        return Hill._names[name.lower()]

    @staticmethod
    def by_rank(rank):
        """
        Return the hill with the given ``rank`` (rank 1 is heighest, then 2,
        etc.).
        """
        if not Hill._hills:
            Hill._load()
        hill = Hill._hills[rank - 1]
        assert hill.rank == rank, 'Hills not ordered by rank'
        return hill

    @staticmethod
    def nearest(coords):
        """
        Returns a tuple (hill, distance) with the hill nearest to the given
        points.
        """
        if not Hill._hills:
            Hill._load()
        d, h = Hill._tree.query([coords._gridx, coords._gridy])
        return Hill._hills[h], d

    @property
    def coords(self):
        return Coords(gridx=self._x, gridy=self._y)

    @property
    def height(self):
        return self._height

    @property
    def hill_id(self):
        return self._id

    @property
    def name(self):
        return self._name

    @property
    def rank(self):
        return self._rank

    @property
    def ranked(self):
        s = str(self._rank)
        if s[-1] in '123':
            if not (self._rank > 10 and s[-2] == '1'):
                return s + 'st' if s[-1] == '1' else s + 'd'
        return s + 'th'

    @property
    def summit(self):
        return f'http://hillsummits.org.uk/htm_summit/{self._id}.htm'

    @property
    def portrait(self):
        return f'http://hillsummits.org.uk/htm_portrait/{self._id}.htm'

    def photo(self):
        """
        Attempts to return a URL with a photo. Returns an empty string if none
        is found.
        """
        def status(url):
            request = urllib.request.Request(url, method='HEAD')
            try:
                with urllib.request.urlopen(request) as f:
                    status = f.status
            except urllib.error.HTTPError:
                status = 404
            return status

        if self._photo is None:
            if status(self.summit) != 404:
                self._photo = self.summit
            elif status(self.portrait) != 404:
                self._photo = self.portrait
            else:
                self._photo = ''
        return self._photo

    def __str__(self):
        return f'{self._name} ({self.height}m)'


def squares():
    """
    Returns a list of tuples ``(name, x, y)`` with two-letter 100km grid square
    names and lower-left corners, covering the area of the data.
    """
    squares = []

    d = 100000
    i0, i1 = 1, 0   # Start on 2nd row (QRSTU)
    for y in range(0, height, d):
        j0, j1 = 2, 0   # Start on 2nd letter (S,N)
        for x in range(0, width, d):
            squares.append((GL[i0][j0] + GL[i1][j1], x, y))
            j1 += 1
            if j1 == 5:
                j1 = 0
                j0 += 1
        i1 += 1
        if i1 == 5:
            i1 = 0
            i0 += 1
    return squares


def linear_interpolant():
    """
    Returns a linear interpolant on the height data.

    Like :meth:`spline()`, this returns a function accepting and x and a y
    argument, that returns a scalar height.
    The height for each grid point ``(i, j)`` is assumed to be in the center of
    the square from ``(i, j)`` to ``(i + 1, j + 1)``.
    """
    if _heights is None:
        gb()
    return linear_interpolation


def linear_interpolation(x, y):
    """
    Returns a linear interpolation of the data at grid coordinates ``(x, y)``
    (in meters).
    """
    ny, nx = _heights.shape
    x, y = x / resolution - 0.5, y / resolution - 0.5

    # Find nearest grid points x1 (left), x2 (right), y1 (bottom), y2 (top).

    # Nearest grid points
    # When outside the grid, we use the _two_ points nearest the edge
    # (resulting in an extrapolation)
    x1 = np.minimum(nx - 2, np.maximum(0, int(x)))
    y1 = np.minimum(ny - 2, np.maximum(0, int(y)))
    x2 = x1 + 1
    y2 = y1 + 1

    # Heights at nearest grid points (subscripts are x_y)
    h11 = _heights[y1, x1]
    h12 = _heights[y2, x1]
    h21 = _heights[y1, x2]
    h22 = _heights[y2, x2]

    # We omit the 1 / (x2 - x1) and 1 / (y2 - y1) terms as these are always 1
    # in the normal (interpolating) case.
    # When extrapolating, we get e.g. x1 == x2, so that (x2 - x) == (x1 - x)

    # X-direction interpolation on both y values
    f1 = np.where(h11 == h21, h11, (x2 - x) * h11 + (x - x1) * h21)
    f2 = np.where(h12 == h22, h12, (x2 - x) * h12 + (x - x1) * h22)

    # Final result
    return np.where(f1 == f2, f1, (y2 - y) * f1 + (y - y1) * f2)

