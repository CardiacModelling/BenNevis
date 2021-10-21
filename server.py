#!/usr/bin/env python3
import logging
import os
import sys
import tempfile

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
                    b = f.read()

            connection.q(
                'final_result',
                msg='Congratulations',
                img=b
            )

        else:
            raise Exception(f'Unexpected message: {message.name}')


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
