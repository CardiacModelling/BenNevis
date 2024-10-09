#!/usr/bin/env python3
#
# First-example code from the README.
# Draws gb-small.png
#

# Import nevis
import nevis

# Download the data (you can skip this step after the first run!)
nevis.download_os_terrain_50()

# Create and store a figure
nevis.write_test_figure("gb-small.png")
