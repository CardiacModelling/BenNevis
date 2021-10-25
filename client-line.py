#!/usr/bin/env python3
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

client = wevis.Client((1, 0, 0), 'explore', 'q4n5nf4508gnv89y6f')

try:
    client.start_blocking()

    r = client.receive_blocking('boundaries')

    lower = np.array([r.get('xlo'), r.get('ylo')])
    upper = np.array([r.get('xhi'), r.get('yhi')])
    print(f'Boundaries: {lower}, {upper}')

    lowth = Score(client)
    x = np.array([0, 0])
    f = lowth(x)



finally:
    client.stop()

# Show result
if not os.path.isdir('results'):
    os.makedirs('results')
path = 'results/result.png'
#print(f'Writing image to {path}.')
#with open(path, 'wb') as f:
#    f.write(r.get('img'))

