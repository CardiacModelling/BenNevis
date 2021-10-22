#!/usr/bin/env python3
import logging
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
defs.add('initial_point', x=float, y=float)
defs.add('ask_height', x=float, y=float)
defs.add('tell_height', z=float)
defs.add('final_answer', x=float, y=float)
defs.add('final_result', msg=str, img=bytes)
defs.instantiate()

username = 'michael' if len(sys.argv) < 2 else sys.argv[1]
client = wevis.Client((1, 0, 0), username, username)

try:
    client.start_blocking()

    r = client.receive_blocking('initial_point')
    x0 = [r.get('x'), r.get('y')]
    print(f'Initial coordinates: {r.get("x")}, {r.get("y")}')

    lowth = Score(client)
    if False:
        x1 = x0
        f1 = lowth(x1)
    else:
        opt = pints.OptimisationController(lowth, x0, method=pints.CMAES)
        x1, f1 = opt.run()

    print(x1)
    print(-f1)

    client.q('final_answer', x=x1[0], y=x1[1])
    r = client.receive_blocking('final_result')

finally:
    client.stop()

# Show result
path = 'result.png'
print(f'Writing image to {path}.')
with open(path, 'wb') as f:
    f.write(r.get('img'))

print()
print(r.get('msg'))

