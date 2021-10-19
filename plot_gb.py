#!/usr/bin/env python3
"""

Attempt to read data from UK Ordinance Survey raster data file
terr50_gagg_gb.zip.

The zip contains several grid squares, using the lettering described here:
https://en.wikipedia.org/wiki/Ordnance_Survey_National_Grid

Inspired by
https://scipython.com/blog/processing-uk-ordnance-survey-terrain-data/

"""
import os
import sys
import urllib.request
import zipfile

import numpy as np

import matplotlib.colors
import matplotlib.pyplot as plt

# Base name of the big zip file to read (e.g. to read 'terr50_gagg_gb.zip' we
# put 'terr50_gagg_gb').
fname = 'terr50_gagg_gb'

# URL to download it from
url = ('https://api.os.uk/downloads/v1/products/Terrain50/downloads?'
       'area=GB&format=ASCII+Grid+and+GML+%28Grid%29&redirect')

# Resolution: distance between neighbours in the grid
resolution = 50

# Full size of the grid to construct (in meters)
# For 'terr50_gagg_gb' we're assuming 700km by 1300km
width, height = 700000, 1300000

# .asc file encoding
ENC = 'utf-8'

# Check Python version
if sys.hexversion < 0x03050000:
    raise RuntimeError('This script requires Python 3.5 or newer.')


def download(url, fname):
    """
    Downloads the (160mb) gagg file from Ordinance Survey.
    """
    if os.path.isfile(fname):
        return

    print(f'File {fname} not found.')
    print(f'Will attempt to download from {url[:40]}...')
    yesno = input(f'Is that OK? (y/n) ')
    if yesno.lower() not in ['y', 'yes']:
        print('Aborting...')
        sys.exit(1)

    print('Downloading...')
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

    # Open zip file
    if print_to_screen:
        print(f'Reading from {basename}.zip')
        i = 0

    with zipfile.ZipFile(f'{basename}.zip', 'r') as f:
        # Browse to inner directory, and then data directory
        dir_data = zipfile.Path(f).joinpath(basename).joinpath('data')

        # Collect paths to inner zip files
        for dir_square in dir_data.iterdir():
            for path in dir_square.iterdir():
                if os.path.splitext(path.name)[1] == '.zip':

                    # Remove zipfile name from path. No idea if there isn't an
                    # easier way to do this...
                    partial_path = str(path)[len(basename) + 5:]

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


# Read data or cached data
nx, ny = width // resolution, height // resolution
cached = f'{fname}.npy'
if os.path.isfile(cached):
    print('Loading...')
    arr = np.load(cached)
else:
    # Ensure zip is downloaded
    download(url, f'{fname}.zip')

    # Create empty array
    arr = np.empty((ny, nx), dtype=np.float32)
    arr.fill(np.nan)

    # Fill it up
    extract(fname, arr, resolution)

    print('Saving...')
    np.save(f'{fname}.npy', arr)

# Replace missing values by far-below-sea level
arr[np.isnan(arr)] = -10

# Fix sea-level issue in Jura & Kintyre
#top = arr[ny // 2:]
#top[np.logical_and(top > 0.8, top < 1.0)] = 0
#top[top > 0] = 1000
#arr[ny // 2:] = top

# Flatten the sea
sea = -5
arr[arr < sea] = sea



# Get extreme points
vmin = np.min(arr)
vmax = np.max(arr)
print(f'Heighest point: {vmax}')

# Downsample
d = 4
if d > 1:
    print(f'Downsampling with factor {d}')
    nx, ny = nx // d, ny // d
    arr = arr[::d, ::d]

# Plot
print('Plotting...')

# Create colormap
# f = absolute height, g = relative to vmax (and zero)
f = lambda x: (x - vmin) / (vmax - vmin)
g = lambda x: f(x * vmax)
cmap = matplotlib.colors.LinearSegmentedColormap.from_list(
    'soundofmusic', [
        (0, '#78b0d1'),             # Deep sea blue
        (f(-4.0), '#78b0d1'),       # Deep sea blue
        (f(-3), '#0f561e'),         # Dark green
        (f(10), '#1a8b33'),         # Nicer green
        (f(100), '#11aa15'),        # Glorious green
        (f(300), '#e8e374'),        # Yellow
        (f(800), '#8a4121'),        # Brownish
        (f(1100), '#999999'),       # Grey
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

png_name = 'gb.png'
fig.savefig(png_name)

try:
    from PIL import Image
    im = Image.open(png_name)
    print(f'Checking PNG size with PIL: {im.size[0]} by {im.size[1]}')
    if im.size == (nx, ny):
        print('OK')
    else:
        print()
except ImportError:
    pass

