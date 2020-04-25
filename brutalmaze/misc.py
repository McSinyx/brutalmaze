# misc.py - module for miscellaneous functions
# Copyright (C) 2017-2020  Nguyễn Gia Phong
#
# This file is part of Brutal Maze.
#
# Brutal Maze is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Brutal Maze is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Brutal Maze.  If not, see <https://www.gnu.org/licenses/>.

__doc__ = 'Brutal Maze module for miscellaneous functions'

from datetime import datetime
from itertools import chain
from math import degrees, cos, sin, pi
from os import path
from random import shuffle

import pygame
from pygame.gfxdraw import filled_polygon, aapolygon
from palace import Buffer, Source

from .constants import ADJACENTS, CORNERS, MIDDLE


def randsign():
    """Return either -1 or 1 (kind of) randomly."""
    return (pygame.time.get_ticks() & 1)*2 - 1


def regpoly(n, R, r, x, y):
    """Return pointlist of a regular n-gon with circumradius of R,
    center point I(x, y) and corner A that angle of vector IA is r
    (in radians).
    """
    r %= pi * 2
    angles = [r + pi*2*side/n for side in range(n)]
    return [(x + R*cos(angle), y + R*sin(angle)) for angle in angles]


def fill_aapolygon(surface, points, color):
    """Draw a filled polygon with anti-aliased edges onto a surface."""
    aapolygon(surface, points, color)
    filled_polygon(surface, points, color)


def sign(n):
    """Return the sign of number n."""
    return -1 if n < 0 else 1 if n else 0


def deg(x):
    """Convert angle x from radians to degrees,
    casted to a nonnegative integer.
    """
    return round((lambda a: a if a > 0 else a + 360)(degrees(x)))


def join(iterable, sep=' ', end='\n'):
    """Return a string which is the concatenation of string
    representations of objects in the iterable, separated by sep.

    end is appended to the resulting string.
    """
    return sep.join(map(str, iterable)) + end


def around(x, y):
    """Return grids around the given one in random order."""
    a = [(x + i, y + j) for i, j in ADJACENTS]
    shuffle(a)
    c = [(x + i, y + j) for i, j in CORNERS]
    shuffle(c)
    return chain(a, c)


def json_rec(directory):
    """Return path to JSON file to be created inside the given directory
    based on current time local to timezone in ISO 8601 format.
    """
    return path.join(
        directory, '{}.json'.format(datetime.now().isoformat()[:19]))


def play(sound: str, x: float = MIDDLE, y: float = MIDDLE,
         gain: float = 1.0) -> Source:
    """Play a sound at the given position."""
    source = Buffer(sound).play()
    source.spatialize = True
    source.position = x, -y, 0
    source.gain = gain
    return source
