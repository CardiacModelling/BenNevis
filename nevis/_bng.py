#!/usr/bin/env python3
"""
Module providing methods to work with BNG (OS36GB) data, specifically the 700
by 1300km grid covering GB.
"""
import csv
import os
import random
import urllib
import zipfile

import bnglonlat
import numpy as np
import scipy.spatial

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


# Full size of the grid (in meters): 700km by 1300km
# Origin is a bottom left (in SV square)
width, height = 700000, 1300000


# Hill names
hill_zip = os.path.join(nevis._DIR_MODULE_DATA, 'hills.zip')
hill_file = 'hills.csv'

# Grid letters (bottom to top, left to right)
GL = [
    ['V', 'W', 'X', 'Y', 'Z'],
    ['Q', 'R', 'S', 'T', 'U'],
    ['L', 'M', 'N', 'O', 'P'],
    ['F', 'G', 'H', 'J', 'K'],
    ['A', 'B', 'C', 'D', 'E'],
]


def dimensions():
    """ Returns the dimensions of the grid (width, height) in meters. """
    return width, height


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


Coords.ben = Coords(gridx=216666, gridy=771288)
Coords.fen = Coords(gridx=520483, gridy=289083)
Coords.pub = {
    #'Ye olde trip to jerusalem': Coords(gridx=457034, gridy=339443},
    'Bear': Coords(gridx=451473, gridy=206135),
    'Canal house': Coords(gridx=457307, gridy=339326),
    'MacSorleys': Coords(gridx=258809, gridy=665079),
    'Sheffield tap': Coords(gridx=435847, gridy=387030),
}
