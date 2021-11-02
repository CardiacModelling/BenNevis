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


class Error(pints.ErrorMeasure):
    """ Turn a height into an error to be minimised. """

    def __init__(self, client):
        self._client = client

    def n_parameters(self):
        return 2

    def __call__(self, p):
        #print(f'  {p[0]:> 9.1f}, {p[1]:> 9.1f}')
        self._client.q('ask_height', x=p[0], y=p[1])
        r = self._client.receive_blocking('send_height')
        return -r.get('z')


def store_image(client, name):
    """ Stores the image embedded in a ``message`` to ``path``. """

    root = 'results'
    path = os.path.join(root, name + '.png')
    if not os.path.isdir(root):
        os.makedirs(root)

    # Get image bytes
    client.q('ask_' + name)
    r = client.receive_blocking('send_' + name)

    # Write to disk
    print(f'Writing image to {path}.')
    with open(path, 'wb') as f:
        f.write(r.get('image'))


defs = wevis.DefinitionList.from_file('data/definitions')
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
    lowth = Error(client)
    if 'debug' in sys.argv:
        x1 = x0 = (upper + lower) / 2
        f1 = lowth(x1)
    else:
        def cb(opt):
            #TODO: We need to update PINTS to get the mean without using
            # undocumented private properties
            p = opt._es.result.xfavorite
            #p = opt.xbest()
            #print(f'{p[0]:> 9.1f}, {p[1]:> 9.1f}')
            client.q('mean', x=p[0], y=p[1])

        x0 = b.sample()
        sigma = min(b.range()) / 6

        opt = pints.OptimisationController(
            lowth, x0, sigma, boundaries=b, method=pints.CMAES)
        opt.set_callback(cb)
        opt.set_max_unchanged_iterations(100, threshold=0.01)
        #opt.optimiser().set_population_size(10)
        x1, f1 = opt.run()

    print('Sending final answer...')
    client.q('final_answer', x=x1[0], y=x1[1])
    r = client.receive_blocking('final_result')
    message = r.get('msg')

    print('Obtaining result figures')
    store_image(client, 'map_full')
    store_image(client, 'map_zoom')
    store_image(client, 'line_plot')

finally:
    client.stop()

print()
print(message)

