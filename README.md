# Where is Ben Nevis?

"Where is Ben Nevis" is a fun(?) project which presents the landscape of Great Britain (GB) as a testbed for numerical optimisation and sampling methods.
Its main component is a Python module called `nevis` which can download height data from the Ordnance Survey, process it to make it more suitable for optimisation, and provide interpolating functions so that it can be treated as a continuous (but not smooth) real-valued function.

## Installation

Python 3.6 or newer is required.

To install from the [Python Package Index (PyPI)](https://pypi.org/project/nevis/), use:
```
pip install nevis
```

To install the optional `convertbng` module at the same time, use:
```
pip install nevis[extras]
```
This will make conversion from points in the data set to longitude and lattitude more accurate.

Developers may wish to skip PyPI installation, clone the [GitHub repository](https://github.com/CardiacModelling/BenNevis), and install from there instead.
Instructions for this are provided in [CONTRIBUTING.md](https://github.com/CardiacModelling/BenNevis/blob/main/CONTRIBUTING.md).

After installing the module, the "OS Terrain 50" data set needs to be downloaded from from the Ordnance Survey website (see the "Data set" section below).
This can be achieved using:
```
import nevis
nevis.download_os_terrain_50()
```
By default, the heights data is installed into `~/nevis-data`.
For example `/home/michael/nevis-data` on a Linux system or `C:\Users\michael\nevis-data` on Windows.
This installation path can be changed by specifying an alternative directory in the environment variable `NEVIS_PATH` before running `download_os_terrain_50()`.

Note that OS Terrain 50 is not part of `nevis` or "Where is Ben Nevis" and comes with its own license.
See [LICENSE.md](https://github.com/CardiacModelling/BenNevis/blob/main/LICENSE.md) for details.

To check that the installation was succesfull, you can plot a height map of GB:

```
# Import nevis
import nevis

# Download the data (you can skip this step after the first run!)
nevis.download_os_terrain_50()

# Create and store a figure
nevis.write_test_figure('gb-small.png')
```

This should create a file (in your working directory) called `gb-small.png`:

![Downscaled map of GB](https://github.com/CardiacModelling/BenNevis/blob/main/gb-small.png)

## Usage

Detailed usage examples will eventually be provided in the [examples](https://github.com/CardiacModelling/BenNevis/blob/main/examples/README.md) directory.
For the time being, please see [fit.py](https://github.com/CardiacModelling/BenNevis/blob/main/fit.py) for an example.

An example of its output is given below:
```

                |>          
 Starting Ben   |   Nevis   
               / \    Local
            /\/---\     0.0.4
           /---    \/\      
        /\/   /\   /  \     
     /\/  \  /  \_/    \    
    /      \/           \   
Minimising error measure
Using Covariance Matrix Adaptation Evolution Strategy (CMA-ES)
Running in sequential mode.
Population size: 100
Iter. Eval.  Best      Current   Time m:s
0     100    -424.4599 -424.4599   0:00.1
1     200    -609.9036 -609.9036   0:00.1
2     300    -609.9036 -555.6289   0:00.2
3     400    -759.5307 -759.5307   0:00.2
20    2100   -951.8221 -740.9721   0:00.4
40    4100   -1268.672 -1257.865   0:00.7
60    6100   -1308.976 -1308.976   0:01.0
80    8100   -1309.1   -1309.1     0:01.3
100   10100  -1309.1   -1309.1     0:01.6
120   12100  -1309.1   -1309.1     0:01.9
140   14100  -1309.1   -1309.1     0:02.1
160   16100  -1309.1   -1309.1     0:02.2
168   16800  -1309.1   -1309.1     0:02.3
Halting: No significant change for 100 iterations.

Saving figure to results/local-map-full.png.
Saving figure to results/local-map-zoom.png.
Saving figure to results/local-line-plot.png.

Congratulations!
You landed at an altitude of 1309m.
  https://opentopomap.org/#marker=15/57.07019/-3.669487
You are 31m from the nearest named hill top, "Ben Macdui",
  ranked the 2d heighest in GB.
  http://hillsummits.org.uk/htm_summit/518.htm
```

### API Documentation

Proper API documentation is still on the [to-do list](https://github.com/CardiacModelling/BenNevis/issues/47).
However, the API is quite small.
The main functions are `linear_interpolant` and `plot`.

A full list follows below:

- British national grid utilities (see `_bng.py`):
  - `ben` Returns grid coordinates for Ben Nevis.
  - `Coords` Represents grid coordinates and can convert to various forms.
  - `dimensions` Returns the physical dimensions (in meters) of the grid.
  - `fen` Returns grid coordinates for Holme Fen, the lowest point (inland).
  - `Hill` Represents a hill from the hills database.
  - `pub` Returns grid coordinates for a random pub, selected from a very short list.
  - `squares` Returns the coordinates of major BNG squares.
- OS Terrain 50 loading methods (see `_os_terrain_50.py`):
  - `DataNotFoundError` An error raised if the data was not downloaded or can't be found.
  - `download_os_terrain_50` The method to download and unpack the data. Only needs to be run once.
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

Height information is from the [OS Terrain 50](https://www.ordnancesurvey.co.uk/business-government/products/terrain-50) data set made available by the UK's Ordnance Survey.

The data is divided into squares indicated with a two letter code, and several data files per square.
Each data file, however, contains its absolute "eastings" and "northings" and so we can ignore the letter codes.
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

Here ``ncols`` and ``nrows`` indicate the number of grid points in the file, the Lower Left corner of the data in the file is given by `xllcorner` and `yllcorner`, and the distance between any two data points is given as `cellsize`.
In the OS Terrain 50 data set, the cellsize is always 50 (giving it its name).
There is a more accurate OS Terrain 5 set that costs money.

According to [Wikipedia](https://en.wikipedia.org/wiki/Ordnance_Survey_National_Grid#Grid_digits), the approximate coordinates for Ben Nevis are 216600, 771200 (which is in the NN17 square).

An easy way to find places on the grid is with https://britishnationalgrid.uk.
Another nice map with BNG coordinates is https://explore.osmaps.com.
A a great map without BNG coordinates can be found at https://opentopomap.org.

### The sea

The sea is a bit messy in these files, as the values depend on mean sea level in each 10x10 km^2 area (OS Tile) relative to OS datum (0m) level [which is mean sea level in Newlyn, Cornwall](https://en.wikipedia.org/wiki/Ordnance_datum).

### Hill tops

Names of hill and mountain tops are taken from [The Database of British and Irish Hills v17.2](http://www.hills-database.co.uk), which is made available under a CC-BY license.
A greatly reduced list, based on this database, is included in `nevis`.
Please see [LICENSE.md](https://github.com/CardiacModelling/BenNevis/blob/main/LICENSE.md) for the licensing information.

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
We also experimented with a scipy [RectBiVariateSpline](https://docs.scipy.org/doc/scipy/reference/generated/scipy.interpolate.RectBivariateSpline.html).
This takes some time (~30 seconds on a fast machine) and uses considerable memory (~3GB).
Most importantly, the spline shows some very serious (and unrealistic) artefacts near high gradients (e.g. at the sea side), so that the linear interpolation seems the way to go for now.

