# Where's Ben Nevis?

This repository contains the source code for the Python module `nevis`: a fun(?) project that presents the landscape of Great Britain (GB) as a test bed for numerical optimisation or sampling methods.

## Installation

Python 3.6 or newer is required.

To install directly from PyPI, use
```
pip install nevis
```
or
```
pip install nevis[extras]
```
to install the optional `convertbng` module as well (this will make conversion from points in the data set to longitude and lattitude more accurate).

Developers may wish to clone and install from the repository, using the instructions in [CONTRIBUTING.md](./CONTRIBUTING.md).

Next, download the "OS Terrain 50" data set (see "Data set" below) from the Ordnance Survey using:
```
import nevis
nevis.load_os50()
```
By default, the data is installed into the user directory `~/nevis-data`, for example `/home/michael/nevis-data` on a Linux system or `C:\Users\michael\nevis-data` on Windows.
The installation path can be changed by specifying an alternative directory in the environment variable `NEVIS_PATH` before running `load_os50()`.

Note that this data set is licensed under the terms explained here: [https://www.ordnancesurvey.co.uk/opendata/licence](https://www.ordnancesurvey.co.uk/opendata/licence).

## Usage

Check that everything was downloaded correctly by plotting a map of Great Britain:

```
# Import nevis
import nevis

# Create and store a figure
nevis.write_test_figure('gb-small.png')
```

![Downscaled map of GB](gb-small.png)

Usage examples are given in the [examples](./examples) directory.

Full API documentation is currently not provided, but there is only a handful of public objects:

- British national grid utilities (see `_bng.py`):
  - `ben` Returns grid coordinates (`Coords`) for Ben Nevis.
  - `Coords` Represents grid coordinates and can convert to various forms.
  - `dimensions` Returns the physical dimensions (in meters) of the grid.
  - `fen` Returns grid coordinates for Holme Fen, the lowest point (inland).
  - `Hill` Represents a hill from the hills database.
  - `pub` Returns grid coordinates for a random pub, selected from a very short list.
  - `squares` Returns the coordinates of major BNG squares.
- OS Terrain 50 loading methods (see `_os50.py`):
  - `DataNotFoundError` An error raised if the data was not downloaded or can't be found.
  - `download_os50` The method to download and unpack the data. Only needs to be run once.
  - `gb` Loads and returns the heights data for GB.
  - `spacing` returns the physical distance (in meters) between the points returned by `gb`.
- Interpolants (see `_interpolation.py`)
  - `linear_interpolant` Returns a linear interpolant over the GB height data.
  - `spline` Returns a spline defined over the GB height data.
- Plotting (see `_plot.py`)
  - `plot` Creates a plot of a map, with optional labels etc.
  - `plot_line` Creates a plot of the height profile between two points.
  - `png_bytes` Turns a matplotlib figure into a `bytes` string.
  - `save_plot` Stores a plot and checks its size. Less paranoid people can use `fig.savefig()` instead.
- Various (see `_util.py` and `__init__.py`)
  - `howdy` Prints some old-school ascii art including the version number.
  - `Timer` Times and formats intervals.
  - `write_test_figure` Loads the data and writes a test figure to disk.

## Data set

Height information is from the [Terrain 50](https://osdatahub.os.uk/downloads/open/Terrain50) data set made available by the UK's Ordnance Survey.
More information can be found [here](https://www.ordnancesurvey.co.uk/business-government/tools-support/terrain-50-support).

The data is divided into squares indicated with a two letter code, and several data files per square.
However, each data file contains its absolute "eastings" and "northings", so we can ignore the letter codes.
Eastings and northings are defined by the "National Grid", or [OSGB36](https://en.wikipedia.org/wiki/Ordnance_Survey_National_Grid).
In easier terms, they are x and y coordinates, in meters, relative to the bottom-left point of the grid (which is the bottom left of the square "SV", which contains the Isles of Scilly).

As an example, the header from the NN17 file is:

```
ncols 200
nrows 200
xllcorner 210000
yllcorner 770000
cellsize 50
```

Here ``ncols`` and ``nrows`` indicate the number of grid points in the file,
the Lower Left corner of the data in the file is given by `xllcorner` and `yllcorner`,
and the distance between any two data points is given as `cellsize`.
In the Terrain 50 data set, the cellsize is always 50 (giving it its name).
There is a more accurate Terrain 5 set that costs money.

According to [Wikipedia](https://en.wikipedia.org/wiki/Ordnance_Survey_National_Grid#Grid_digits), the approximate coordinates for Ben Nevis are 216600, 771200 (which is in the NN17 square).

An easy way to find places on the grid is with https://britishnationalgrid.uk.
Another nice map with BNG coordinates is https://explore.osmaps.com.
A a great map without BNG coordinates can be found at https://opentopomap.org.

### The sea

The sea is a bit messy in these files, as the values depend on mean sea level in each 10x10 km^2 area (OS Tile) relative to OS datum (0m) level [which is mean sea level in Newlyn, Cornwall](https://en.wikipedia.org/wiki/Ordnance_datum).

### Hill tops

Names of hill and mountain tops are taken from [The Database of British and Irish Hills v17.2](http://www.hills-database.co.uk), which is made available under a CC-BY license.

### Lattitude and longitude 🐇🕳️

What about longitude (east-west) and lattitude (north-south)?
These are defined, it seems, by [WGS 84](https://en.wikipedia.org/wiki/World_Geodetic_System#WGS84), although there is a Europe-specific version called ETRS89 which "for most purposes ... can be considered equivalent to WGS84" (["Transformations and OSGM15 User Guide"](https://www.ordnancesurvey.co.uk/business-government/tools-support/os-net/for-developers)).
Transforming from national grid coordinates to longitude and lattitude is hard, and the Ordnance Survey have released a thing called [OSTN15](https://www.ordnancesurvey.co.uk/business-government/tools-support/os-net/for-developers) to do this.
Although this still seems to result in x, y coordinates, not degrees.
Luckily, somebody's [made a tool for it](https://github.com/urschrei/convertbng).
Unfortunately, some people have issues installing this, so that we rely on a [less accurate fallback](https://github.com/MichaelClerx/bnglonlat) for the time being.
If you can, please manually install `convertbng` too (BenNevis will try using this first, before switching to `bnglonglat`).

### Interpolation

To get heights for arbitrary points, we need to interpolate.
By default, we use a linear interpolant.
We also experimented with a scipy [RectBiVariateSpline](https://docs.scipy.org/doc/scipy/reference/reference/generated/scipy.interpolate.RectBivariateSpline.html).
This takes some time (~30 seconds on a fast machine) and uses considerable memory (~3GB).
Most importantly, the spline shows some very serious (and unrealistic) artefacts near high gradients (e.g. at the sea side), so that the linear interpolation seems the way to go for now.

