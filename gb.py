#!/usr/bin/env python3
#
# Load the data and plot a map of GB.
#
import os
import sys

import nevis

# Get normalised coordinates
ben = None
if len(sys.argv) == 3:
    ben = nevis.Coords(normx=sys.argv[1], normy=sys.argv[2])

# Show some points
points = trajectory = None
if False:
    import numpy as np
    ben = nevis.ben()
    points = [np.array(ben.grid)]
    for i in range(50):
        points.append(points[-1] + (np.random.random(2) - 0.5) * 1e5)
    points = np.array(points)
    trajectory = [np.array(ben.grid)]
    for i in range(20):
        trajectory.append(trajectory[-1] + (np.random.random(2) - 0.5) * 1e5)
    trajectory = np.array(trajectory)

# Load data
arr = nevis.gb()

# Create plot
# downsampling=27 makes the plot fit on my screen at 100% zoom.
fig, ax, arr = nevis.plot(
    arr, ben=ben, trajectory=trajectory, points=points, downsampling=27)

# Save plot, and check resulting image dimensions
if not os.path.isdir('results'):
    os.makedirs('results')
nevis.save_plot('results/gb.png', fig, arr)

