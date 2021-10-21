#!/usr/bin/env python3
import logging
import os
import sys
import tempfile

import numpy as np
import scipy.interpolate
import wevis

import nevis


class BenNevisUser(wevis.User):

    def __init__(self, username):
        super().__init__(username)

        # Set transformations and rotation
        self._scaling = np.exp(25 * (np.random.random() - 0.5))
        r = np.random.random() * 2 * np.pi
        self._rotation = np.array(
            [[np.cos(r), -np.sin(r)], [np.sin(r), np.cos(r)]])


class BenNevisServer(wevis.Room):
    def __init__(self, heights, function):
        super().__init__()
        self._d = heights
        self._f = function

    def handle(self, connection, message):

        if message.name == 'ask_height':
            x, y = message.get('x', 'y')
            z = self._f(x, y)
            connection.q('tell_height', z=z)

        elif message.name == 'final_answer':
            x, y = message.get('x', 'y')

            # Create figure
            fig, ax, data = nevis.plot(
                self._d,
                ben=(x, y),
                downsampling=3 if 'debug' in sys.argv else 27,
                silent=True
            )
            del(data)

            # Get figure bytes
            with tempfile.TemporaryDirectory() as d:
                path = os.path.join(d, 'result.png')
                fig.savefig(path)
                del(fig)
                with open(path, 'rb') as f:
                    img = f.read()

            # Get nearest hill top
            c = nevis.Coords(normx=x, normy=y)
            h, d = nevis.Hill.nearest(c)
            d = int(round(d))
            msg = (f'Congratulations! You landed {d} meters from {h.name}'
                   f' {c.google}')

            # Send reply
            connection.q('final_result', msg=msg, img=img)

        else:
            raise Exception(f'Unexpected message: {message.name}')


def version_validator(major, minor, revision):
    return True


def user_validator(username, password, salt):
    plain = {
        'michael': 'mypassword'
    }
    try:
        if password == wevis.encrypt(plain[username], salt):
            return BenNevisUser(username)
    except KeyError:
        pass
    return False


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
    t = nevis.Timer()
    s = scipy.interpolate.RectBivariateSpline(
        np.arange(0, ny),
        np.arange(0, nx),
        heights)
    f = lambda x, y: s(y * ny, x * nx)[0][0]
    print(f'Completed in {t.format()}')

    wevis.set_logging_level(logging.INFO)
    defs = wevis.DefinitionList()
    defs.add('ask_height', x=float, y=float)
    defs.add('tell_height', z=float)
    defs.add('final_answer', x=float, y=float)
    defs.add('final_result', msg=str, img=bytes)
    defs.instantiate()
    room = BenNevisServer(heights, f)
    server = wevis.Server(version_validator, user_validator, room)
    server.launch()
