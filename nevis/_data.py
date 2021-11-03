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
import os
import pickle
import random
import sys
import urllib.request
import zipfile

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


def extract(basename, arr, resolution, print_to_screen=True):
    """
    Extracts data from an "ASCII Grid and GML (Grid)" file at ``basename``.zip,
    and extracts the data into numpy array ``arr``.

    The resolution of each file inside the zip must be the same, and must be
    specified as ``resolution``.
    """
    fname = os.path.join(data, f'{basename}.zip')

    # Open zip file
    if print_to_screen:
        print(f'Reading from {fname}')
        i = 0

    with zipfile.ZipFile(fname, 'r') as f:
        # Browse to inner directory, and then data directory
        dir_data = zipfile.Path(f).joinpath(basename).joinpath('data')

        # Collect paths to inner zip files
        for dir_square in dir_data.iterdir():
            for path in dir_square.iterdir():
                if os.path.splitext(path.name)[1] == '.zip':
                    # Remove zipfile name from path. No idea if there isn't an
                    # easier way to do this...
                    partial_path = str(path)[len(fname) + 1:]

                    # Read .asc data from embedded zip file
                    read_nested_zip(f, partial_path, arr, resolution)

                    if print_to_screen:
                        i += 1
                        print('.', end=(None if i % 79 == 0 else ''))
                        sys.stdout.flush()

    if print_to_screen:
        print('\nDone')


def read_nested_zip(parent, name, arr, resolution):
    """
    Opens a zip-in-a-zip and reads any ``.asc`` files inside it.
    """
    # Open zip-in-a-zip
    with parent.open(name) as raw:
        with zipfile.ZipFile(raw) as f:

            # Scan for asc files
            for path in f.namelist():
                if os.path.splitext(path)[1] == '.asc':

                    # Read internal asc
                    with f.open(path, 'r') as asc:
                        try:
                            read_asc(asc, arr, resolution)
                        except Exception as e:
                            raise Exception(
                                f'Error reading {path} in {name}: {str(e)}.')


def read_asc(handle, arr, resolution):
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
    arr[yll:yll + nrows, xll:xll + ncols] = data[::-1, :]


def gb():
    """
    Returns an array of elevation data for Great Brittain, with height in
    meters and grid points spaced 50m apart.

    Array indices are (height, width) i.e. (longitude, latitude).

    If required, the data is first downloaded (approx 160MB) and unpacked
    (approx 1.5GB).
    """

    # Read data or cached data
    nx, ny = width // resolution, height // resolution
    cached = os.path.join(data, terrain_file + '.npy')
    if os.path.isfile(cached):
        print('Loading terrain data...')
        arr = np.load(cached)
    else:
        # Ensure zip is downloaded
        download(url, f'{terrain_file}.zip')

        # Create empty array
        arr = np.empty((ny, nx), dtype=np.float32)
        arr.fill(np.nan)

        # Fill it up
        extract(terrain_file, arr, resolution)

        print(f'Saving to {cached}...')
        np.save(cached, arr)

    # Replace missing values by far-below-sea level
    arr[np.isnan(arr)] = -10

    # Flatten the sea
    sea = -5
    arr[arr < sea] = sea

    return arr


def spline(heights):
    """
    Create a spline interpolating over an array of heights.
    """
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
            heights)
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
        Hill._tree = scipy.spatial.KDTree(np.array(coords))

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

