#!/usr/bin/env python3
import logging
import os
import random
import sys
import tempfile

import numpy as np
import scipy.interpolate
import wevis

import nevis


class BenNevisUser(wevis.User):

    def __init__(self, username):
        super().__init__(username)

        # Status
        self.has_finished = False

        # Scaling: We start from x,y,z all in meters, and then scale by the
        # same factor to ensure a result that preserves angles.
        self._scale = np.exp(25 * (np.random.random() - 0.5))

        # Rotation
        r = np.random.random() * 2 * np.pi
        self._rotation = np.array(
            [[np.cos(r), -np.sin(r)], [np.sin(r), np.cos(r)]])

        if username == 'debug':
            self._scale = 1
            self._rotation = np.eye(2)

    def grid_to_mystery(self, x, y, z=None):
        """ Translate grid coordinates (meters) to mystery coordinates. """
        return np.dot(self._rotation, np.array([x, y]) * self._scale)

    def mystery_to_grid(self, x, y):
        """ Translate mystery coordinates to grid coordinates (meters). """
        return np.dot(self._rotation.T, np.array([x, y])) / self._scale

    def mystery_height(self, z):
        """ Translate a real height in meters into a mystery height. """
        return z * self._scale

    @staticmethod
    def validate(username, password, salt):
        """ Validate a username. """
        tokens = {
            'debug': 'debug',
            'ben': 'ben',
            'michael': 'michael',
        }
        try:
            if password == wevis.encrypt(tokens[username], salt):
                return BenNevisUser(username)
        except KeyError:
            pass
        return False


class BenNevisServer(wevis.Room):
    def __init__(self, heights, function):
        super().__init__()
        self._d = heights
        self._f = function

    def handle(self, connection, message):

        if message.name == 'ask_height':
            if connection.user.has_finished:
                connection.q('error', 'Final answer already given.')
                return

            x, y = message.get('x', 'y')
            x, y = connection.user.mystery_to_grid(x, y)
            z = self._f(x, y)
            #print(f'query {x} {y} {z}')
            connection.q('tell_height', z=connection.user.mystery_height(z))

        elif message.name == 'final_answer':
            connection.user.has_finished=True

            x, y = message.get('x', 'y')
            x, y = connection.user.mystery_to_grid(x, y)
            c = nevis.Coords(gridx=x, gridy=y)

            # Create figure
            d = 3 if 'debug' in sys.argv else 27
            fig, ax, data = nevis.plot(
                self._d, ben=c, downsampling=d, silent=True)
            del(data)

            # Get figure bytes
            with tempfile.TemporaryDirectory() as d:
                path = os.path.join(d, 'result.png')
                fig.savefig(path)
                del(fig)
                with open(path, 'rb') as f:
                    img = f.read()

            # Get nearest hill top
            h, d = nevis.Hill.nearest(c)
            dm = f'{round(d)}m' if d < 1000 else f'{round(d / 1000, 1)}km'
            msg = (f'You landed at {c.google}. The nearest hill top is'
                   f' "{h.name}", {dm} away.')
            if d < 50:
                msg = f'Congratulations! {msg}'
            elif d < 1000:
                msg = f'Good job! {msg}'
            else:
                msg = f'Interesting! {msg}'

            # Send reply
            connection.q('final_result', msg=msg, img=img)

        else:
            raise Exception(f'Unexpected message: {message.name}')

    def welcome(self, connection):

        # Send user initial point
        if connection.user.name == 'ben':
            c = nevis.ben()
        else:
            c = nevis.pub('Canal house')
        x, y = connection.user.grid_to_mystery(c.gridx, c.gridy)
        connection.q('initial_point', x=x, y=y)


def version_validator(major, minor, revision):
    return True


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout)

    # Load data
    heights = nevis.gb()

    # Downsample a lot, for testing
    if 'debug' in sys.argv:
        print('DEBUG MODE: downsampling')
        d = 9
        heights = heights[::d, ::d]

    print('Reticulating splines...')
    ny, nx = heights.shape
    w, h = nevis.dimensions()
    c = 25  # Correction: Coords at lower-left, height is center of square
    t = nevis.Timer()
    s = scipy.interpolate.RectBivariateSpline(
        np.linspace(0, h, ny, endpoint=False) + 25,
        np.linspace(0, w, nx, endpoint=False) + 25,
        heights)
    f = lambda x, y: s(y, x)[0][0]
    print(f'Completed in {t.format()}')


    wevis.set_logging_level(logging.INFO)
    defs = wevis.DefinitionList()
    defs.add('initial_point', x=float, y=float)
    defs.add('ask_height', x=float, y=float)
    defs.add('tell_height', z=float)
    defs.add('final_answer', x=float, y=float)
    defs.add('final_result', msg=str, img=bytes)
    defs.add('error', msg=str)
    defs.instantiate()
    room = BenNevisServer(heights, f)
    server = wevis.Server(version_validator, BenNevisUser.validate, room)
    server.launch()
