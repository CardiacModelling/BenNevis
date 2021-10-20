#!/usr/bin/env python3
import logging
import sys

import numpy as np
import scipy.interpolate
import wevis

import nevis


def version_validator(major, minor, revision):
    return True


def user_validator(username, password, salt):
    if username == 'michael' and password == wevis.encrypt('mypassword', salt):
        return wevis.User('michael')
    return False


class BenNevisServer(wevis.Room):
    def __init__(self, function):
        super().__init__()
        self._f = function


    def handle(self, connection, message):

        if message.name == 'query':
            x, y = message.get('x', 'y')
            z = self._f(x, y)
            connection.q('response', z=z)
        else:
            raise Exception(f'Unexpected message: {message.name}')


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout)

    # Load data
    arr = nevis.gb()

    # Downsample a lot, for testing
    d = 8
    arr = arr[::d, ::d]

    ny, nx = arr.shape

    print(arr.shape)

    print('Reticulating splines...')
    t = nevis.Timer()
    y = np.arange(0, arr.shape[0])
    x = np.arange(0, arr.shape[1])
    s = scipy.interpolate.RectBivariateSpline(y, x, arr)
    f = lambda x, y: s(x * nx, y * ny)[0][0]

    print('Testing')
    print(f(0, 0))
    print(f(0.4, 0.4))
    print(f(0.42, 0.22))

    b = nevis.Timer()
    z = [f(*np.random.random(2)) for i in range(10)]
    print(t.format())

    print('Setting up server')
    wevis.set_logging_level(logging.INFO)
    defs = wevis.DefinitionList()
    defs.add('query', x=float, y=float)
    defs.add('response', z=float)
    defs.instantiate()

    room = BenNevisServer(f)
    server = wevis.Server(version_validator, user_validator, room)
    server.launch()
