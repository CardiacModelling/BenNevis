#!/usr/bin/env python3
#
# Create a spline.
#
import numpy as np
import scipy.interpolate

import nevis

# Load data
arr = nevis.gb()

# Downsample a lot, for testing
d = 8
arr = arr[::d, ::d]

print(arr.shape)

if False:
    y = np.linspace(0, 1, arr.shape[0])
    x = np.linspace(0, 1, arr.shape[1])
else:
    y = np.arange(0, arr.shape[0])
    x = np.arange(0, arr.shape[1])


print('Reticulating splines...')
t = nevis.Timer()
s = scipy.interpolate.RectBivariateSpline(y, x, arr)
f = lambda x, y: s(x, y)[0][0]
print(t.format())

print('Testing')
print(f(0, 0))
#print(f(0.5, 0.5))
print(f(1000, 1234))
print(arr[1000, 1234])

