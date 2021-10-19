#!/usr/bin/env python3
"""
Provides the method :meth:`data.gb()` that returns elevation data for Great
Brittain, obtained from the Ordinance Survey data set ``terr50_gagg_gb``.
"""
# The zip contains several grid squares, using the lettering described here:
# https://en.wikipedia.org/wiki/Ordnance_Survey_National_Grid
#
# Inspired by
# https://scipython.com/blog/processing-uk-ordnance-survey-terrain-data/
#
import os
import sys
import urllib.request
import zipfile

import numpy as np

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


def download(url, fname):
    """
    Downloads the (160mb) gagg file from Ordinance Survey.
    """
    if os.path.isfile(fname):
        return

    print(f'File {fname} not found.')
    print(f'Will attempt to download from {url[:40]}...')
    yesno = input('Is that OK? (y/n) ')
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

    # Flatten the sea
    sea = -5
    arr[arr < sea] = sea

    return arr

