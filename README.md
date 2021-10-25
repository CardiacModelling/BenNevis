# Where is Ben Nevis?

This repository contains the first files for a fun(?) project that tests optimisation methods on Ordnance Survey (OS) data for Great Britain.

## Requirements

Python 3.8 or higher, with pip-installable dependencies listed in `requirements.txt` (you can install these with `pip install -r requirements.txt`).

When first run, this script will download the data from the OS (about 160MB) and then convert it to a NumPy array stored on disk (about 1.5GB).

## Usage

Run `plot_gb.py`.
Don't worry, it'll be a lot faster the 2nd time.

The amount of downscaling can be set using the variable ``downsampling``.
An example with ``downsampling=32`` is shown below.

![Downscaled map of GB](gb-small.png)

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

According to wikiepedia, the approximate coordinates for Ben Nevis are 216600, 771200 (which is in the NN17 square).

An easy way to find places on the grid is with https://britishnationalgrid.uk

### The sea

The sea is a bit messy in these files, as the values depend on e.g. the tide at the time of measuring.

### Hill tops

Names of hill and mountain tops are taken from [The Database of British and Irish Hills v17.2](http://www.hills-database.co.uk), which is available under a CC-BY license.

### Lattitude and longitude 🐇🕳️

What about longitude (east-west) and lattitude (north-south)?
These are defined, it seems, by [WGS 84](https://en.wikipedia.org/wiki/World_Geodetic_System#WGS84), although there is a Europe-specific version called ETRS89 which "for most purposes ... can be considered equivalent to WGS84" (["Transformations and OSGM15 User Guide"](https://www.ordnancesurvey.co.uk/business-government/tools-support/os-net/for-developers)).
Transforming from national grid coordinates to longitude and lattitude is hard, and the Ordnance Survey have released a thing called [OSTN15](https://www.ordnancesurvey.co.uk/business-government/tools-support/os-net/for-developers) to do this.
Although this still seems to result in x, y coordinates, not degrees.
Luckily, somebody's [made a tool for it](https://github.com/urschrei/convertbng).



