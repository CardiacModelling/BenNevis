#!/usr/bin/env python3
import logging
import os
import sys

import numpy as np
import wevis

import nevis


# Maximum number of evaluations per user (per connection)
MAX_EVALS = 100000


class BenNevisUser(wevis.User):

    # Log-in credentials
    _user_tokens = None

    def __init__(self, username):
        super().__init__(username)

        # Status
        self.has_finished = False
        self.n_evals = 0

        #
        # Transformation
        #

        # Rotation around center
        d = np.array(nevis.dimensions())
        self._center = d / 2
        r = np.random.random() * 2 * np.pi
        self._rotation = np.array(
            [[np.cos(r), -np.sin(r)], [np.sin(r), np.cos(r)]])

        # Translation: we translate x, y, z by some fixed degree
        self._translation = (np.random.random(2) - 0.5) * d

        # Boundaries
        edges = np.array([
            self.grid_to_mystery(x, y)
            for x, y in ((0, 0), (0, d[1]), (d[0], 0), (d[0], d[1]))
        ])
        self.lower = np.min(edges, axis=0)
        self.upper = np.max(edges, axis=0)

        # TODO: Use some scaling? (Equal on x, y, and z)

        #
        # Result logging
        #

        # Requested points and trajectory
        self.points = []
        self.trajectory = []

        # Final position (in meters)
        self.c = None

        # Hill and distance
        self.hd = None

        # Avoid overhead of repeated figure making
        self.map_full_sent = False
        self.map_zoom_sent = False
        self.line_plot_sent = False

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
    def validate(username, password, salt, version):
        """ Validate a username. """
        if BenNevisUser._user_tokens is None:
            BenNevisUser._load_user_tokens()
        token = BenNevisUser._user_tokens.get(username, '')
        if token == '' or password != wevis.encrypt(token, salt):
            return False
        return BenNevisUser(username)


class BenNevisServer(wevis.Room):
    def __init__(self, function):
        super().__init__()
        self._f = function

    def handle(self, connection, message):
        user = connection.user

        if message.name == 'ask_height':
            if user.has_finished:
                return connection.q('error', 'Final answer already given.')
            if user.n_evals >= MAX_EVALS:
                return connection.q(
                    'error',
                    'Maximum number of evaluations reached ({MAX_EVALS}).')

            user.n_evals += 1
            x, y = message.get('x', 'y')
            x, y = user.mystery_to_grid(x, y)
            z = self._f(x, y)
            #print(f'query {x} {y} {z}')
            user.points.append((x, y))
            connection.q('send_height', z=z)

        elif message.name == 'ask_heights':
            if user.has_finished:
                return connection.q('error', 'Final answer already given.')

            xs, ys = message.get('xs', 'ys')
            n = len(xs)
            if len(ys) != n:
                return connection.q('X and Y array must have same length.')
            if user.n_evals + n > MAX_EVALS:
                return connection.q(
                    'error',
                    'Maximum number of evaluations reached ({MAX_EVALS}).')
            user.n_evals += n

            zs = [None] * n
            for i, x, y in zip(range(n), xs, ys):
                x, y = user.mystery_to_grid(x, y)
                z = zs[i] = self._f(x, y)
                user.points.append((x, y))
            connection.q('send_heights', zs=zs)

        elif message.name == 'mean':
            if user.has_finished:
                connection.q('error', 'Final answer already given.')
                return

            x, y = message.get('x', 'y')
            x, y = user.mystery_to_grid(x, y)
            user.trajectory.append((x, y))

        elif message.name == 'final_answer':
            if user.has_finished:
                return connection.q('error', 'Final answer already given.')
            user.has_finished = True
            t = nevis.Timer()

            # Get user coordinates
            x, y = message.get('x', 'y')
            x, y = user.mystery_to_grid(x, y)
            z = self._f(x, y)
            c = user.c = nevis.Coords(gridx=x, gridy=y)

            # Get nearest hill top
            h, d = user.hd = nevis.Hill.nearest(c)
            dm = f'{round(d)}m' if d < 1000 else f'{round(d / 1000, 1)}km'
            p = h.photo()
            p = ': ' + p if p else ''
            z = int(round(float(z)))
            msg = (f'You landed at an altitude of {z}m, near {c.opentopomap}.'
                   f' You are {dm} from the nearest named hill top,'
                   f' "{h.name}", ranked the {h.ranked} heighest in GB{p}.')
            if d < 100:
                msg = f'Congratulations! {msg}'
            elif d < 1000:
                msg = f'Good job! {msg}'
            else:
                msg = f'Interesting! {msg}'

            # Convert visited points and/or trajectory
            user.points = np.array(user.points)
            if user.trajectory:
                user.trajectory = np.array(user.trajectory)
            else:
                user.trajectory = user.points
                user.points = None

            # Send reply
            connection.q('final_result', msg=msg)
            self.log.info(f'Final answer processed in {t.format()}')

        elif message.name == 'ask_map_full':
            if not user.has_finished:
                return connection.q('error', 'Final answer needed first.')
            elif user.map_full_sent:
                return connection.q('error', 'map_full already sent')
            user.map_full_sent = True
            t = nevis.Timer()

            # Figure 1: Full map
            h, d = user.hd
            downsampling = 3 if '-debug' in sys.argv else 27
            labels = {
                'Ben Nevis': nevis.ben(),
                h.name: h.coords,
                'You': user.c,
            }
            fig, ax, data, _ = nevis.plot(
                labels=labels,
                trajectory=user.trajectory,
                points=user.points,
                downsampling=downsampling,
                silent=True)
            img = nevis.png_bytes(fig)
            connection.q('send_map_full', image=img)
            self.log.info(f'Full map created and sent in {t.format()}')

        elif message.name == 'ask_map_zoom':
            if not user.has_finished:
                return connection.q('error', 'Final answer needed first.')
            elif user.map_zoom_sent:
                return connection.q('error', 'map_zoom already sent')
            user.map_zoom_sent = True
            t = nevis.Timer()

            # Figure 2: Zoomed map
            x, y = user.c.grid
            h, d = user.hd
            b = 20e3
            boundaries = [x - b, x + b, y - b, y + b]
            downsampling = 1
            labels = {
                'Ben Nevis': nevis.ben(),
                h.name: h.coords,
                'You': user.c,
            }
            fig, ax, data, _ = nevis.plot(
                boundaries=boundaries,
                labels=labels,
                trajectory=user.trajectory,
                points=user.points,
                downsampling=downsampling,
                silent=True)
            img = nevis.png_bytes(fig)
            connection.q('send_map_zoom', image=img)
            self.log.info(f'Zoom map created and sent in {t.format()}')

        elif message.name == 'ask_line_plot':
            if not user.has_finished:
                return connection.q('error', 'Final answer needed first.')
            elif user.line_plot_sent:
                return connection.q('error', 'line_plot already sent')
            user.line_plot_sent = True
            t = nevis.Timer()

            # Figure 3: Line from known top to you
            c = user.c
            h, d = user.hd
            fig, ax, p1, p2 = nevis.plot_line(
                self._f, user.c, h.coords, 'You', h.name)
            img = nevis.png_bytes(fig)
            connection.q('send_line_plot', image=img)
            self.log.info(f'Line plot created and sent in {t.format()}')

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


if __name__ == '__main__':
    level = logging.INFO
    if '-verbose' in sys.argv:
        level = logging.DEBUG
        wevis.set_logging_level(level)
    logging.basicConfig(stream=sys.stdout, level=level)

    # Load data and spline
    nevis.howdy()
    nevis.gb(9 if '-debug' in sys.argv else 1)
    #f = nevis.spline()
    f = nevis.linear_interpolant()

    # Load user tokens
    BenNevisUser.load_user_tokens()

    defs = wevis.DefinitionList.from_file('data/definitions')
    defs.instantiate()
    room = BenNevisServer(f)
    server = wevis.Server(BenNevisUser.validate, room)
    server.launch()
