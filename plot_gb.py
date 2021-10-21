#!/usr/bin/env python3
#
# Load the data and plot a map of GB.
#
import nevis
import sys

# Get normalised coordinates
ben = None
if len(sys.argv) == 3:
    ben = nevis.Coords(normx=sys.argv[1], normy=sys.argv[2])

# Load data
arr = nevis.gb()

# Create plot
# downsampling=27 makes the plot fit on my screen at 100% zoom.
fig, ax, arr = nevis.plot(arr, ben=ben, downsampling=27)

# Save plot, and check resulting image dimensions
nevis.save_plot('gb.png', fig, arr)

