#!/usr/bin/env python3
import os
import sys

import matplotlib.cm
import numpy as np

import nevis

# Don't downsample
sys.argv = [x for x in sys.argv if x != '-debug']

# Load height data
nevis.howdy('Spline check')
heights = nevis.gb()
ny, nx = heights.shape
r = nevis.spacing()
r2 = r // 2             # Height is taken at center of grid square

# Create (or load cached) spline
f = nevis.spline()

#
# Squares and objects to draw on the maps
#
# Squares as (square, lines), where each square is (xlo, xhi, ylo, yhi) and
# each line is (x0, x1, y0, y1)
squares = []
# Labels as name : Coords
labels = {}

#
# Squares of about 15x15km look OK
#
# The grid is in 50m by 50m squares, and the height should be taken in the
# middle, so to draw horizontal, vertical, or diagonal lines that align with
# the grid, each number should end in 25 or 75.
#

#
# Ben Nevis 216666 771288
#
labels['Ben Nevis'] = nevis.ben()
square = [210000, 224000, 764000, 778000]
lines = []
# Vertical, across peak, through valley
lines.append([216675, 216675, 771525, 769025])
# Horizontal, from valley up to peak
lines.append([214025, 216825, 771275, 771275])
# Diagonal, into valley
lines.append([216725, 216725 - 2700, 771325, 771325 - 2700])

squares.append((square, lines))

#
# The (firth of) clyde near Dumbarton Rock NS 4001 7391
#
labels['Dumbarton rock'] = nevis.Coords.from_square('NS 39931 74494')
#         239784  239931  672520  674494
square = [233000, 247000, 667000, 681000]
lines = []
# Near Rock, vertical, to hill on other side
lines.append([239925, 239925, 674475, 672525])
# Near Rock, horizontal
lines.append([239925, 239225, 674475, 674475])
squares.append((square, lines))

#
# Margate, near Dreamland and its Scenic Railway coaster 635107, 170534
#
labels['Scenic railway'] = nevis.Coords.from_square('TR 35107 70534')
square = [630000, 645000, 159000, 174000]
lines = []
# From margate vertically into the sea
lines.append([635125, 635125, 170225, 171825])
# Through a river and into the sea
lines.append([633125, 636125, 161825, 161825])
squares.append((square, lines))

#
# Teignmouth beach SX 9441 7301
#

#
# Sea issue NT68: Coast near North Berwick 359353, 682985
#
square = [357000, 371000, 676500, 690500]
lines = []
# Through square, horizontally
lines.append([360025, 369975, 684025, 684025])
# Through square, vertically
lines.append([365025, 365025, 680025, 689975])
squares.append((square, lines))
# Through below-sea level "land" in square below
lines.append([362825, 362825, 677925, 680525])
squares.append((square, lines))

#
# Sea issues NR35,24,34,44,33: Islay, south-east coast
#
labels['Laphroig'] = nevis.Coords(138639, 645208)
labels['Lagavulin'] = nevis.Coords(140190, 645660)
labels['Ardbeg'] = nevis.Coords(141478, 646419)
square = [119000, 151000, 629000, 661000]
lines = []
# Horizontally through squares
lines.append([130025, 132975, 652025, 652025])
lines.append([129025, 129025, 649975, 647025])
lines.append([120025, 149975, 645025, 645025])
lines.append([130025, 139975, 635025, 635025])
squares.append((square, lines))

#
# Sea issues: NR56,57: Jura south-east coast
#
labels['Jura distillery'] = nevis.Coords(152809, 666895)
square = [144000, 166000, 659000, 681000]
lines = []
# Horizontally through squares
lines.append([156025, 159975, 672025, 672025])
lines.append([153025, 159975, 666025, 666025])
lines.append([150025, 159975, 661525, 661525])
squares.append((square, lines))

#
# Sea issues: NR65,64,74,76,75: North-west Kintyre and south-west Knapdale
#
square = [159000, 181000, 639000, 671000]
lines = []
# Through NR76
lines.append([170025, 179975, 661525, 661525])
lines.append([171225, 171225, 669975, 660025])
lines.append([160025, 175025, 655025, 655025])
lines.append([160025, 169975, 645025, 645025])
lines.append([165025, 165025, 659975, 640025])
squares.append((square, lines))

#
# Ensure results directory exists
#
root = 'results'
if not os.path.isdir(root):
    os.makedirs(root)

#
# Figure: Full map
#
cmap = matplotlib.cm.get_cmap('tab10', 10)
fig, ax, data, g = nevis.plot(
    downsampling=27,
    silent=True)
for ii, sq in enumerate(squares):
    square, line = sq
    x0, x1, y0, y1 = square
    x0, y0 = g(x0, y0)
    x1, y1 = g(x1, y1)
    a, b = [x0, x1, x1, x0, x0], [y0, y0, y1, y1, y0]
    ax.plot(a, b, 'w', lw=3)
    ax.plot(a, b, label=f'Square {ii + 1}')
ax.legend(loc='upper left')
path = os.path.join(root, 'spline-check-0-map-full.png')
print()
print(f'Saving figure to {path}.')
fig.savefig(path)

#
# Figure 2: Zoomed maps
#
for ii, sq in enumerate(squares):
    square, lines = sq
    fig, ax, data, g = nevis.plot(
        boundaries=square,
        labels=labels,
        downsampling=1,
        small_grid=True,
        silent=True)
    for jj, line in enumerate(lines):
        x0, x1, y0, y1 = line
        a0, b0 = g(x0, y0)
        a1, b1 = g(x1, y1)
        c, d = 0.1 * (a1 - a0), 0.1 * (b1 - b0)
        color = cmap(jj) if jj < 2 else cmap(1 + jj)
        ax.plot([a0, a1], [b0, b1], label=f'line {jj + 1}', color=color)
        ax.plot(
            [a1, a1 - c + d, a1 - c - d, a1],
            [b1, b1 - d - c, b1 - d + c, b1],
            color=color)
    if lines:
        ax.legend(loc='lower right')

    path = os.path.join(root, f'spline-check-{ii + 1}-0-map.png')
    print(f'Saving figure to {path}.')
    fig.savefig(path)

    # Figure 3: Line from known top to you
    for jj, line in enumerate(lines):
        x0, x1, y0, y1 = line
        p0, p1 = nevis.Coords(x0, y0), nevis.Coords(x1, y1)
        fig, ax, q0, q1 = nevis.plot_line(f, p0, p1, figsize=(14, 10))
        ax.minorticks_on()
        ax.grid(which='major')
        ax.grid(which='minor', color='#eeeeee')
        label = f'Line {jj + 1}'

        # Compare with grid points
        if x0 % r == x1 % r == y0 % r == y1 % r == r2:

            # Vertical line
            if x0 == x1:
                i0 = q0.grid[1] // r
                i1 = q1.grid[1] // r
                j0 = x0 // r
                ts = r * (np.arange(0, 1 + abs(i1 - i0)) - abs(y0 // r - i0))
                s = 1 if i1 > i0 else -1
                #ys = [f(x0, y0 + t * s) for t in ts]
                ss = np.arange(i0, i1 + s, s)
                ss = [heights[s, j0] for s in ss]
                #ax.plot(ts, ys, 'x', label='Spline values')
                ax.plot(ts, ss, '+', label='Data values')
                if np.min(ss) <= 0 and np.max(ss) >= 0:
                    ax.axhline(0, color='k', lw=0.5, alpha=0.2)
                ax.legend(loc='center left')
                label += ', Vertical'

            elif y0 == y1:
                i0 = y0 // r
                j0 = q0.grid[0] // r
                j1 = q1.grid[0] // r
                ts = r * (np.arange(0, 1 + abs(j1 - j0)) - abs(x0 // r - j0))
                s = 1 if j1 > j0 else -1
                #ys = [f(x0 + t * s, y0) for t in ts]
                ss = np.arange(j0, j1 + s, s)
                ss = [heights[i0, s] for s in ss]
                #ax.plot(ts, ys, 'x', label='Spline values')
                ax.plot(ts, ss, '+', label='Data values')
                if np.min(ss) <= 0 and np.max(ss) >= 0:
                    ax.axhline(0, color='k', lw=0.5, alpha=0.4)
                ax.legend(loc='center left')
                label += ', Horizontal'

            elif (y1 - y0 == x1 - x0):
                pad = min(abs(q0.grid[0] - x0), abs(q0.grid[1] - y0)) // r
                sx = 1 if x1 > x0 else -1
                sy = 1 if y1 > y0 else -1
                j0 = x0 // r - pad * sx
                j1 = x1 // r + pad * sx
                i0 = y0 // r - pad * sy
                i1 = y1 // r + pad * sy
                tjs = r * (np.arange(0, 1 + abs(j1 - j0)) - abs(x0 // r - j0))
                tis = r * (np.arange(0, 1 + abs(i1 - i0)) - abs(y0 // r - i0))
                #sp = [
                #    f(x0 + ti * sx, y0 + tj * sy) for ti, tj in zip(tis, tjs)]
                sx = np.arange(j0, j1 + sx, sx)
                sy = np.arange(i0, i1 + sy, sy)
                ss = [heights[j, i] for j, i in zip(sy, sx)]
                ts = np.sqrt(tjs**2 + tis**2) * np.sign(tjs)
                #ax.plot(ts, sp, 'x', label='Spline values')
                ax.plot(ts, ss, '+', label='Data values')
                if np.min(ss) <= 0 and np.max(ss) >= 0:
                    ax.axhline(0, color='k', lw=0.5, alpha=0.2)
                ax.legend(loc='center left')
                label += ', Diagonal'

            fig.text(0.99, 0.97, label, ha='right', va='center')

        path = os.path.join(root, f'spline-check-{ii + 1}-{jj + 1}-line.png')
        print(f'Saving figure to {path}.')
        fig.savefig(path)

