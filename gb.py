#!/usr/bin/env python3
#
# Load the data and plot a map of GB.
#
import os
import sys

import nevis

# Get normalised coordinates
if len(sys.argv) == 3:
    labels = {'User point': nevis.Coords(normx=sys.argv[1], normy=sys.argv[2])}
else:
    labels = {'Ben Nevis': nevis.ben()}

# Show some points
points = trajectory = None
if True:
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
boundaries = None
downsampling = 27
if True:
    b = nevis.ben().grid
    d = 50e3
    boundaries = [b[0] - d, b[0] + d, b[1] - d, b[1] + d]
    downsampling = 2

# Load data
arr = nevis.gb()

# Create plot
# downsampling=27 makes the plot fit on my screen at 100% zoom.
fig, ax, arr = nevis.plot(
    arr,
    boundaries=boundaries,
    labels=labels,
    trajectory=trajectory,
    points=points,
    downsampling=downsampling)

# Save plot, and check resulting image dimensions
if not os.path.isdir('results'):
    os.makedirs('results')
nevis.save_plot('results/gb.png', fig, arr)

