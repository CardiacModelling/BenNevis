#!/usr/bin/env python3
import logging
import sys

import numpy as np
import pints
import wevis

logging.basicConfig(stream=sys.stdout)

defs = wevis.DefinitionList()
defs.add('query', x=float, y=float)
defs.add('response', z=float)
defs.instantiate()

client = wevis.Client((1, 0, 0), 'michael', 'mypassword')

def f(x, y):
    client.q('query', x=x, y=y)
    r = client.receive_blocking('response')
    return r.get('z')

try:
    client.start_blocking()

    print(f(0, 0))
    print(f(0.4, 0.4))
    print(f(0.42, 0.22))
    print()

    t = pints.Timer()
    z = [f(*np.random.random(2)) for i in range(10)]
    print(t.format())
    print()
    print(z)

finally:
    client.stop()
