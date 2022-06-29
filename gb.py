#!/usr/bin/env python3
#
# Loads the data and plot a map of GB.
# Extra command-line arguments can be used to show only part of the data, e.g.
#
#   python gb.py NY12
#
import os
import sys

import nevis

# Say hi
nevis.howdy()

# Downsampling and boudnaries
boundaries = None
downsampling = 27

# Show grid
big_grid = True
small_grid = False

# Zoom in on a grid square
try:
    square = nevis.Coords.from_square_with_size(sys.argv[1])
except Exception:
    square = None
if square:
    x, y = square[0].grid
    r = nevis.spacing()
    boundaries = [x, x + square[1] - r, y, y + square[1] - r]
    downsampling = 1 if square[1] > 50000 else 1
    small_grid = True

# Show some points
points = trajectory = None
if False:
    import numpy as np
    ben = nevis.ben()
    points = []
    trajectory = [np.array(ben.grid)]
    for i in range(50):
        trajectory.append(
            trajectory[-1] + (np.random.random(2) - 0.5) * 5e2 * i**1.5)
        for j in range(10):
            points.append(
                trajectory[-1] + (np.random.random(2) - 0.5) * 8e2 * i**1.5)
    trajectory = np.array(trajectory)
    points = np.array(points)

# Zoom in on an area
if False:
    b = nevis.ben().grid
    d = 20e3
    boundaries = [b[0] - d, b[0] + d, b[1] - d, b[1] + d]
    downsampling = 1
    small_grid = True

# Labels
labels = {
    'Ben Nevis': nevis.ben(),
    'Holme Fen': nevis.fen(),
}

# Load data
nevis.gb()

# Create plot
# downsampling=27 makes the plot fit on my screen at 100% zoom.
fig, ax, heights, g = nevis.plot(
    boundaries=boundaries,
    labels=labels,
    trajectory=trajectory,
    points=points,
    big_grid=big_grid,
    small_grid=small_grid,
    downsampling=downsampling,
    silent=False,
)

# Save plot, and check resulting image dimensions
if not os.path.isdir('results'):
    os.makedirs('results')
nevis.save_plot('results/gb.png', fig, heights, silent=False)

