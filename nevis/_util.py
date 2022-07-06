#!/usr/bin/env python3
"""
Provides utility methods (i.e. methods not directly related to ``nevis``).
"""
import timeit

import nevis


class Timer(object):
    """
    Provides accurate timing.

    Example
    -------
    ::

        timer = nevis.Timer()
        print(timer.format(timer.time()))

    """

    def __init__(self, output=None):
        self._start = timeit.default_timer()
        self._methods = {}

    def format(self, time=None):
        """
        Formats a (non-integer) number of seconds, returns a string like
        "5 weeks, 3 days, 1 hour, 4 minutes, 9 seconds", or "0.0019 seconds".
        """
        if time is None:
            time = self.time()
        if time < 1e-2:
            return str(time) + ' seconds'
        elif time < 60:
            return str(round(time, 2)) + ' seconds'
        output = []
        time = int(round(time))
        units = [
            (604800, 'week'),
            (86400, 'day'),
            (3600, 'hour'),
            (60, 'minute'),
        ]
        for k, name in units:
            f = time // k
            if f > 0 or output:
                output.append(str(f) + ' ' + (name if f == 1 else name + 's'))
            time -= f * k
        output.append('1 second' if time == 1 else str(time) + ' seconds')
        return ', '.join(output)

    def reset(self):
        """
        Resets this timer's start time.
        """
        self._start = timeit.default_timer()

    def time(self):
        """
        Returns the time (in seconds) since this timer was created, or since
        meth:`reset()` was last called.
        """
        return timeit.default_timer() - self._start


#
# Version-related methods
#
def howdy(name='Local'):
    """ Say hi the old fashioned way. """
    print('')
    print('                |>          ')
    print(' Starting Ben   |   Nevis   ')
    print('               / \    ' + name)
    print('            /\/---\     ' + nevis.__version__)
    print('           /---    \/\      ')
    print('        /\/   /\   /  \     ')
    print('     /\/  \  /  \_/    \    ')
    print('    /      \/           \   ')


def print_result(x, y, z):
    """
    Print information about an optimisation result.

    Arguments:

    ``x``
        The x-coordinate of the result.
    ``y``
        The y-coordinate of the result.
    ``z``
        The z-coordinate of the result.
    """

    coords = nevis.Coords(gridx=x, gridy=y)
    hill, distance = nevis.Hill.nearest(coords)
    print('Congratulations!' if distance < 100 else (
        'Good job!' if distance < 1000 else 'Interesting!'))
    print(f'You landed at an altitude of {round(z)}m.')
    print(f'  {coords.opentopomap}')
    dm = (
        f'{round(distance)}m' if distance < 1000
        else f'{round(distance / 1000, 1)}km'
    )
    print(f'You are {dm} from the nearest named hill top, "{hill.name}",')
    print(f'  ranked the {hill.ranked} heighest in GB.')
    photo = hill.photo()
    if photo:
        print('  ' + photo)
