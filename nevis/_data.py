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
import random
import sys
import urllib.request
import zipfile

import convertbng.util as bng
import numpy as np
import scipy.spatial

import nevis


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


class Coords(object):
    """
    Coordinates, either normalised (so that 0, 0 is the bottom left of the grid
    and 1, 1 is the top right) or as OS36GB grid points in meters.

    Examples::

        p = Coords(gridx=123456, gridy=123456)
        print(p.grid)
        print(p.normalised)

        p = Coords(normx=0.5, normy=0.2)
        print(p.grid)
        print(p.normalised)

    """
    def __init__(self, gridx=None, gridy=None, normx=None, normy=None):
        self.gridx = self.gridy = None
        self.normx = self.normy = None

        if gridx is not None and gridy is not None:
            if normx is None and normy is None:
                self.gridx = int(gridx)
                self.gridy = int(gridy)
                self.normx = self.gridx / width
                self.normy = self.gridy / height
        if normx is not None and normy is not None:
            if gridx is None and gridy is None:
                self.normx = float(normx)
                self.normy = float(normy)
                self.gridx = int(self.normx * width)
                self.gridy = int(self.normy * height)
        if self.gridx is None:
            raise ValueError(
                'Either (gridx and gridy) or (normx and normy) must be'
                'specified (and not both).')

        self._latlong = None

    @property
    def grid(self):
        return self.gridx, self.gridy

    @property
    def normalised(self):
        return self.normx, self.normy

    @property
    def latlong(self):
        if self._latlong is None:
            long, lat = bng.convert_lonlat([self.gridx], [self.gridy])
            self._latlong = lat[0], long[0]
        return self._latlong

    #@property
    #def geograph(self):
    #    return f'http://www.geograph.org.uk/gridref/NN8371434465
    # Requires the grid letters!

    @property
    def google(self):
        lat, long = self.latlong
        return (
            'https://www.google.com/maps/@?api=1&map_action=map'
            f'&center={lat},{long}&zoom=15&basemap=terrain')

    def __str__(self):
        return f'Coords({int(round(self.gridx))}, {int(round(self.gridy))})'


def dimensions():
    """ Returns the dimensions of the grid (width, height) in meters. """
    return width, height


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

        print(Hill.by_name('Ben Nevis')
        print(Hill.by_rank(1))
        print(Hill.by_rank(2))
        print(Hill.by_rank(3))

        h, d = Hill.nearest(Coords(gridx=216600, gridy=771300))
        print(h)

    """
    _hills = []
    _names = {}
    _tree = None

    def __init__(self, x, y, rank, height, name):
        if Hill._tree is not None:
            raise ValueError('Cannot add hills after tree construction.')
        self._x = int(x)
        self._y = int(y)
        self._rank = int(rank)
        self._height = float(height)
        self._name = name.strip()
        Hill._hills.append(self)
        Hill._names[self._name.lower()] = self

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
        fields = ['x', 'y', 'rank', 'meters', 'name']
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
        d, h = Hill._tree.query([coords.gridx, coords.gridy])
        return Hill._hills[h], d

    @property
    def coords(self):
        return Coords(gridx=self._x, gridy=self._y)

    @property
    def height(self):
        return self._height

    @property
    def name(self):
        return self._name

    @property
    def rank(self):
        return self._rank

    def __str__(self):
        return f'{self._name} ({self.height}m)'

