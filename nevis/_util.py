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
            return str(time) + " seconds"
        elif time < 60:
            return str(round(time, 2)) + " seconds"
        output = []
        time = int(round(time))
        units = [
            (604800, "week"),
            (86400, "day"),
            (3600, "hour"),
            (60, "minute"),
        ]
        for k, name in units:
            f = time // k
            if f > 0 or output:
                output.append(str(f) + " " + (name if f == 1 else name + "s"))
            time -= f * k
        output.append("1 second" if time == 1 else str(time) + " seconds")
        return ", ".join(output)

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
def howdy(name="version"):
    """Say hi the old fashioned way."""
    print(r"")
    print(r"                |>          ")
    print(r" Starting Ben   |   Nevis   ")
    print(r"               / \    " + name)
    print(r"            /\/---\     " + nevis.__version__)
    print(r"           /---    \/\      ")
    print(r"        /\/   /\   /  \     ")
    print(r"     /\/  \  /  \_/    \    ")
    print(r"    /      \/           \   ")


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
    print(
        "Congratulations!"
        if distance < 100
        else ("Good job!" if distance < 1000 else "Interesting!")
    )
    print(f"You landed at an altitude of {round(z)}m.")
    print(f"  {coords.opentopomap}")
    dm = (
        f"{round(distance)}m"
        if distance < 1000
        else f"{round(distance / 1000, 1)}km"
    )
    print(f'You are {dm} from the nearest named hill top, "{hill.name}",')
    print(f"  ranked the {hill.ranked} highest in GB.")
    photo = hill.photo()
    if photo:
        print("  " + photo)


def generate_kml(
    path,
    labels=None,
    trajectory=None,
    points=None,
):
    """
    Generate a KML (Keyhole Markup Language, used to display geographic data
    in an Earth browser such as Google Earth) file from given data.

    For a description of the KML format, see
    https://developers.google.com/kml/documentation/kml_tut

    Arguments:

    ``path``
        The path of the file to write to.
    ``labels``
        An optional dictionary mapping string labels to points (tuples in
        meters or Coords objects) that will be marked on the map. The points
        will be shown as green pinpoints with text labels beside them.
    ``trajectory``
        An optional array of shape ``(n_points, 2)`` indicating the trajectory
        to be plotted (points specified in meters). All the points along the
        trajectory will be shown as small orange pinpoints with labels of
        their index prefixed with "T" (e.g. "T3"). The trajectory itself will
        be shown as a red curve extended down to the ground connecting
        adjacent points.
    ``points``
        An optional array of shape ``(n_points, 2)`` indicating points on the
        map (points specified in meters). All the points will be shown as small
        blue pinpoints with labels of their index prefixed with "P" (e.g.
        "P3").

    ``lables``, ``trajectory``, and ``points`` can be used simultaneously.
    """
    from pykml.factory import KML_ElementMaker as KML
    from lxml import etree

    def make_coords(x, y):
        """
        Convert a pair of coordinates (in meters) to a KML coordinates string.
        """
        lat, lon = nevis.Coords(x, y).latlong
        return f"{lon},{lat}"

    marks = []
    if labels is not None:
        for label, p in labels.items():
            if isinstance(p, nevis.Coords):
                p = p.grid
            x, y = p

            marks.append(
                KML.Placemark(
                    KML.name(label),
                    KML.Point(KML.coordinates(make_coords(x, y))),
                    KML.styleUrl("#label_icon_style"),
                )
            )

    if points is not None:
        for i, (x, y) in enumerate(points):
            marks.append(
                KML.Placemark(
                    KML.name(f"P{i}"),
                    KML.Point(KML.coordinates(make_coords(x, y))),
                    KML.styleUrl("#points_icon_style"),
                )
            )

    if trajectory is not None:
        for i, (x, y) in enumerate(trajectory):
            marks.append(
                KML.Placemark(
                    KML.name(f"T{i}"),
                    KML.Point(KML.coordinates(make_coords(x, y))),
                    KML.styleUrl("#trajectory_icon_style"),
                )
            )

        marks.append(
            KML.Placemark(
                KML.name("Trajectory"),
                KML.styleUrl("#line_style"),
                KML.LineString(
                    KML.coordinates(
                        " ".join([make_coords(x, y) for x, y in trajectory])
                    ),
                    KML.extrude(1),
                    KML.tessellate(1),
                ),
            )
        )

    icon_url = "http://maps.google.com/mapfiles/kml/paddle/wht-blank.png"

    doc = KML.kml(
        KML.Document(
            KML.name("Nevis Project"),
            KML.Style(
                KML.LineStyle(
                    KML.color("ff1400FF"),
                    KML.width(3),
                ),
                id="line_style",
            ),
            KML.Style(
                KML.IconStyle(
                    KML.Icon(
                        KML.href(icon_url),
                    ),
                    KML.color("ff00FF14"),
                ),
                id="label_icon_style",
            ),
            KML.Style(
                KML.IconStyle(
                    KML.Icon(
                        KML.href(icon_url),
                    ),
                    KML.scale(0.5),
                    KML.color("ffFF7800"),
                ),
                KML.LabelStyle(
                    KML.scale(0.5),
                ),
                id="points_icon_style",
            ),
            KML.Style(
                KML.IconStyle(
                    KML.Icon(
                        KML.href(icon_url),
                    ),
                    KML.scale(0.5),
                    KML.color("ff1e90ff"),
                ),
                KML.LabelStyle(
                    KML.scale(0.5),
                ),
                id="trajectory_icon_style",
            ),
            *marks,
        )
    )

    with open(path, "w") as fobj:
        fobj.write(etree.tostring(doc, pretty_print=True).decode("utf-8"))
