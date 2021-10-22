#!/usr/bin/env python3
#
# Example client program that performs a fit with CMA-ES
#
import logging
import os
import sys

import numpy as np
import pints
import wevis

logging.basicConfig(stream=sys.stdout)


class Score(pints.ErrorMeasure):
    def __init__(self, client):
        self._client = client

    def n_parameters(self):
        return 2

    def __call__(self, p):
        self._client.q('ask_height', x=p[0], y=p[1])
        r = self._client.receive_blocking('tell_height')
        return -r.get('z')


defs = wevis.DefinitionList()
defs.add('boundaries', xlo=float, xhi=float, ylo=float, yhi=float)
defs.add('ask_height', x=float, y=float)
defs.add('tell_height', z=float)
defs.add('final_answer', x=float, y=float)
defs.add('final_result', msg=str, img=bytes)
defs.instantiate()

client = wevis.Client((1, 0, 0), 'test', 'ps4w69uebj2af3jcON')

try:
    print('Starting client...')
    client.start_blocking()

    # Create boundaries
    print('Waiting for boundaries...')
    r = client.receive_blocking('boundaries')
    lower = np.array([r.get('xlo'), r.get('ylo')])
    upper = np.array([r.get('xhi'), r.get('yhi')])
    b = pints.RectangularBoundaries(lower, upper)

    print('Starting optimisation...')
    lowth = Score(client)
    if 'debug' in sys.argv:
        x1 = x0 = np.array([0, 0])
        f1 = lowth(x1)
    else:
        x0 = b.sample()
        opt = pints.OptimisationController(lowth, x0, method=pints.CMAES)
        x1, f1 = opt.run()

    client.q('final_answer', x=x1[0], y=x1[1])
    r = client.receive_blocking('final_result')

finally:
    client.stop()

# Show result
if not os.path.isdir('results'):
    os.makedirs('results')
path = 'results/client-fit-result.png'
print(f'Writing image to {path}.')
with open(path, 'wb') as f:
    f.write(r.get('img'))

print()
print(r.get('msg'))

