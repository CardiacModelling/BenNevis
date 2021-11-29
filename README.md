# Where is Ben Nevis?

This repository contains the first files for a fun(?) project that tests optimisation methods on Ordnance Survey (OS) data for Great Britain.

## Requirements

Python 3.6 or higher, with pip-installable dependencies listed in `requirements.txt` (you can install these with `pip install -r requirements.txt`).
The additional package `convertbng` is recommended, but not required.

When first run, this script will download the data from the OS (about 160MB) and then convert it to a NumPy array stored on disk (about 1.5GB).

## Usage

### First run: plot a map of GB

After downloading, run `gb.py` to download and unpack the data and test that all went well by plotting a map of great brittain.
(Don't worry, it'll be a lot faster the 2nd time.)

The amount of downscaling can be set using the variable ``downsampling``.
An example with ``downsampling=32`` is shown below.

![Downscaled map of GB](gb-small.png)

### Running a fit

Next, you can start `fit.py` to run a fit.
Results will be stored in the `results` directory.
This directory will also contain some other files, such as an `.npy` file storing a [cached](https://numpy.org/doc/stable/reference/generated/numpy.load.html) numpy representation of the downloaded terrain data (and optionally a file called `spline` that stores a [cached](https://docs.python.org/3/library/pickle.html) spline).

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

According to wikipedia, the approximate coordinates for Ben Nevis are 216600, 771200 (which is in the NN17 square).

An easy way to find places on the grid is with https://britishnationalgrid.uk.
Another nice map with BNG coordinates is https://explore.osmaps.com.
A a great map without BNG coordinates can be found at https://opentopomap.org.

### The sea

The sea is a bit messy in these files, as the values depend on e.g. the tide at the time of measuring.

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
We also experimented with a scipy [RectBiVariateSpline])https://docs.scipy.org/doc/scipy/reference/reference/generated/scipy.interpolate.RectBivariateSpline.html).
This takes some time (~30 seconds on a fast machine) and uses considerable memory (~3GB).
Most importantly, the spline shows some very serious (and unrealistic) artefacts near high gradients (e.g. at the sea side), so that the linear interpolation seems the way to go for now.

## Tiny API docs

Proper API docs might be added at some point.
For now, there are only a handful of public objects:

- data utilities (see `_data.py` for details):
  - `ben` returns grid coordinates (`Coords`) for Ben Nevis
  - `Coords` represents grid coordinates and can convert to various forms
  - `dimensions` returns the physical dimensions (in meters) of the GB height data
  - `fen` returns grid coordinates for Holme Fen, the lowest point (inland)
  - `gb` loads and returns the heights data for GB
  - `Hill` represents a hill from the hills database
  - `linear_interpolant` returns a linear interpolant over the GB height data
  - `pub` returns grid coordinates for a random pub, selected from a very short list
  - `spacing` returns the physical distance (in meters) between grid points
  - `spline` returns a spline defined over the GB height data
  - `squares` returns the coordinates of major BNG squares
- plotting utilities (see `_plot.py` for details)
  - `plot` creates a plot of a map, with optional labels etc.
  - `plot_line` creates a plot of the height profile between two points
  - `png_bytes` turns a matplotlib figure into a `bytes` string
  - `save_plot` stores a plot and checks its size (only for paranoid people)
- others (see `_util.py` for details)
  - `Timer` times and formats intervals

