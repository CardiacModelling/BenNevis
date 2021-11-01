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

    # Log-in credentials
    _user_tokens = None

    def __init__(self, username):
        super().__init__(username)

        # Status
        self.has_finished = False

        # Rotation around center
        d = np.array(nevis.dimensions())
        self._center = d / 2
        r = np.random.random() * 2 * np.pi
        self._rotation = np.array(
            [[np.cos(r), -np.sin(r)], [np.sin(r), np.cos(r)]])

        # Translation: we translate x, y, z by some fixed degree
        self._translation = (np.random.random(2) - 0.5) * d

        # Allow exploration by special user
        if username == 'explore':
            self._rotation = np.eye(2)
            self._translation = np.zeros(2)

        # Boundaries
        edges = np.array([
            self.grid_to_mystery(x, y)
            for x, y in ((0, 0), (0, d[1]), (d[0], 0), (d[0], d[1]))
        ])
        self.lower = np.min(edges, axis=0)
        self.upper = np.max(edges, axis=0)
        if username != 'explore':
            self.lower *= 1.1 + 0.2 * np.random.random(2)
            self.upper *= 1.1 + 0.2 * np.random.random(2)

        # Requested points
        self.points = []
        self.means = []

    def grid_to_mystery(self, x, y):
        """ Translate grid coordinates (meters) to mystery coordinates. """
        return (np.dot(self._rotation, np.array([x, y]) - self._center)
                + self._translation)

    def mystery_to_grid(self, x, y):
        """ Translate mystery coordinates to grid coordinates (meters). """
        return (np.dot(self._rotation.T,
                       (np.array([x, y]) - self._translation)) + self._center)

    @staticmethod
    def load_user_tokens():
        """ Load login tokens. """
        BenNevisUser._user_tokens = {
            'test': 'ps4w69uebj2af3jcON',
            'explore': 'q4n5nf4508gnv89y6f',
        }

        path = 'data/tokens'
        if not os.path.isfile(path):
            return
        print(f'Reading user login tokens from {path}')
        tokens = {}
        try:
            with open(path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    user, token = line.split(':', 2)
                    user = user.strip()
                    token = token.strip()
                    if user and token:
                        tokens[user] = token
                    else:
                        raise ValueError('Empty user and/or token')
        except Exception as e:
            raise RuntimeError(
                f'Unable to parse user tokens from {path}') from e

    @staticmethod
    def validate(username, password, salt):
        """ Validate a username. """
        if BenNevisUser._user_tokens is None:
            BenNevisUser._load_user_tokens()
        token = BenNevisUser._user_tokens.get(username, '')
        if token == '' or password != wevis.encrypt(token, salt):
            return False
        return BenNevisUser(username)


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
            connection.user.points.append((x, y))
            connection.q('tell_height', z=z)

        elif message.name == 'mean':
            x, y = message.get('x', 'y')
            x, y = connection.user.mystery_to_grid(x, y)
            connection.user.means.append((x, y))

        elif message.name == 'final_answer':
            connection.user.has_finished = True

            # Get user coordinates
            x, y = message.get('x', 'y')
            x, y = connection.user.mystery_to_grid(x, y)
            c = nevis.Coords(gridx=x, gridy=y)

            # Get nearest hill top
            h, d = nevis.Hill.nearest(c)
            dm = f'{round(d)}m' if d < 1000 else f'{round(d / 1000, 1)}km'
            msg = (f'You landed at {c.opentopomap}. The nearest namedhill top'
                   f' is "{h.name}", {dm} away: {h.photo()}.')
            if d < 100:
                msg = f'Congratulations! {msg}'
            elif d < 1000:
                msg = f'Good job! {msg}'
            else:
                msg = f'Interesting! {msg}'

            # Get visited points and/or trajectory
            points = np.array(connection.user.points)
            if connection.user.means:
                trajectory = np.array(connection.user.means)
            else:
                trajectory = points
                points = None

            # Figure 1: Full map
            downsampling = 3 if 'debug' in sys.argv else 27
            labels = {
                'Ben Nevis': nevis.ben(),
                h.name: h.coords,
                'You': c,
            }
            fig, ax, data = nevis.plot(
                self._d,
                labels=labels,
                trajectory=trajectory,
                points=points,
                downsampling=downsampling,
                silent=True)
            img1 = figure_bytes(fig)
            del(fig, ax, data)

            # Figure 2: Zoomed map
            d = 20e3
            downsampling = 1
            boundaries = [x - d, x + d, y - d, y + d]
            fig, ax, data = nevis.plot(
                self._d,
                boundaries=boundaries,
                labels=labels,
                trajectory=trajectory,
                points=points,
                downsampling=downsampling,
                silent=True)
            img2 = figure_bytes(fig)
            del(fig, ax, data)

            # Send reply
            connection.q('final_result', msg=msg, img1=img1, img2=img2)

        else:
            raise Exception(f'Unexpected message: {message.name}')

    def user_enter(self, connection):

        # Send user boundaries
        user = connection.user
        connection.q(
            'boundaries',
            xlo=user.lower[0],
            ylo=user.lower[1],
            xhi=user.upper[0],
            yhi=user.upper[1],
        )

    def user_exit(self, user):
        pass


def version_validator(major, minor, revision):
    return True


def figure_bytes(fig):
    """ Convert a figure to bytes for transmission. """
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, 'result.png')
        fig.savefig(path)
        del(fig)
        with open(path, 'rb') as f:
            return f.read()


if __name__ == '__main__':
    level = logging.INFO
    if 'verbose' in sys.argv:
        level = logging.DEBUG
        wevis.set_logging_level(level)
    logging.basicConfig(stream=sys.stdout, level=level)

    print('                           ')
    print(' Starting Ben      Nevis   ')
    print('               /\    Server')
    print('            /\/--\         ')
    print('           /---   \/\      ')
    print('        /\/   /\  /  \     ')
    print('     /\/  \  /  \/    \    ')
    print('    /      \/          \   ')

    # Load user tokens
    BenNevisUser.load_user_tokens()

    # Load data
    heights = nevis.gb()

    # Downsample a lot, for testing
    if 'debug' in sys.argv:
        d = 9
        print(f'DEBUG MODE: downsampling with factor {d}')
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

    defs = wevis.DefinitionList.from_file('data/definitions')
    defs.instantiate()
    room = BenNevisServer(heights, f)
    server = wevis.Server(version_validator, BenNevisUser.validate, room)
    server.launch()
