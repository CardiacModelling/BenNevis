#!/usr/bin/env python3
import os
import sys

import numpy as np
import pints

import nevis


print('                          ')
print(' Starting Ben      Nevis  ')
print('               /\    Local')
print('            /\/--\        ')
print('           /---   \/\     ')
print('        /\/   /\  /  \    ')
print('     /\/  \  /  \/    \   ')
print('    /      \/          \  ')
print('')

# Load height data
heights = nevis.gb()

# Downsample a lot, for testing
if '-debug' in sys.argv:
    d = 9
    print(f'DEBUG MODE: downsampling with factor {d}')
    heights = heights[::d, ::d]

# Create (or load cached) spline
f = nevis.spline(heights)

# Visited points, and means per iteration
points = []
trajectory = []


# Create pints error measure
class Error(pints.ErrorMeasure):
    """
    Turn a height into an error to be minimised.

    Writes to global var: not suitable for parallelistion!
    """
    def __init__(self, spline):
        self.f = spline

    def n_parameters(self):
        return 2

    def __call__(self, p):
        points.append(p)
        return -self.f(*p)


# Create callback to store means
def cb(opt):
    trajectory.append(opt._es.result.xfavorite)
    #trajectory.append(opt.xbest())


# Create pints boundaries
w, h = nevis.dimensions()
b = pints.RectangularBoundaries([0, 0], [w, h])

#
# Run!
#
e = Error(f)
x0 = b.sample()
s0 = min(b.range()) / 6
opt = pints.OptimisationController(
    e,
    x0=b.sample(),
    sigma0=min(b.range()) / 6,
    boundaries=b,
    method=pints.CMAES
)
opt.set_callback(cb)
opt.set_max_unchanged_iterations(100, threshold=0.01)
x1, f1 = opt.run()

# Get final result and some comparison points
x, y = x1
z = int(round(f(x, y)))
c = nevis.Coords(gridx=x, gridy=y)
h, d = nevis.Hill.nearest(c)

# Visited points
points = np.array(points)
trajectory = np.array(trajectory)

# Ensure results directory exists
root = 'results'
if not os.path.isdir(root):
    os.makedirs(root)


#
# Figure 1: Full map
#
downsampling = 3 if '-debug' in sys.argv else 27
labels = {
    'Ben Nevis': nevis.ben(),
    h.name: h.coords,
    'You': c,
}
fig, ax, data = nevis.plot(
    heights,
    labels=labels,
    trajectory=trajectory,
    points=points,
    downsampling=downsampling,
    silent=True)
path = os.path.join(root, 'local-map-full.png')
print()
print(f'Saving figure to {path}.')
fig.savefig(path)

#
# Figure 2: Zoomed map
#
b = 20e3
boundaries = [x - b, x + b, y - b, y + b]
downsampling = 1
labels = {
    'Ben Nevis': nevis.ben(),
    h.name: h.coords,
    'You': c,
}
fig, ax, data = nevis.plot(
    heights,
    boundaries=boundaries,
    labels=labels,
    trajectory=trajectory,
    points=points,
    downsampling=downsampling,
    silent=True)
path = os.path.join(root, 'local-map-zoom.png')
print(f'Saving figure to {path}.')
fig.savefig(path)


# Figure 3: Line from known top to you
fig, ax, p1, p2 = nevis.plot_line(f, c, h.coords, 'You', h.name)
path = os.path.join(root, 'local-line-plot.png')
print(f'Saving figure to {path}.')
fig.savefig(path)

#
# Print results
#
print()
print('Congratulations!' if d < 100 else (
      'Good job!' if d < 1000 else 'Interesting!'))
print(f'You landed at an altitude of {z}m.')
print(f'  {c.opentopomap}')

dm = f'{round(d)}m' if d < 1000 else f'{round(d / 1000, 1)}km'
print(f'You are {dm} from the nearest named hill top, "{h.name}",')
print(f'  ranked the {h.ranked} heighest in GB.')
p = h.photo()
if p:
    print('  ' + p)
print()

