# -*- coding: utf-8 -*-
# characters.py - module for shared functions and macros
# This file is part of brutalmaze
#
# brutalmaze is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# brutalmaze is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with brutalmaze.  If not, see <http://www.gnu.org/licenses/>.
#
# Copyright (C) 2017 Nguyễn Gia Phong

__doc__ = 'brutalmaze module for hero and enemy classes'

from functools import reduce
from math import cos, sin, pi
from operator import or_
from random import uniform

import pygame
from pygame.gfxdraw import filled_polygon, aapolygon

from .constants import MIDDLE


def some(a, keys):
    """Return True if there is a key k in keys that bool(a[k]) is True."""
    return bool(reduce(or_, (a[k] for k in keys)))


def round2(number):
    """Round a number to an int."""
    return int(round(number))


def randsign():
    """Return either -1 or 1 (kind of) randomly."""
    return (pygame.time.get_ticks() & 1)*2 - 1


def regpoly(n, R, r, x, y):
    """Return the pointlist of the regular polygon with n sides,
    circumradius of R, the center point I(x, y) and one point A make the
    vector IA with angle r (in radians).
    """
    r %= pi * 2
    angles = [r + pi*2*side/n for side in range(n)]
    return [(x + R*cos(angle), y + R*sin(angle)) for angle in angles]


def fill_aapolygon(surface, points, color):
    """Draw a filled polygon with anti aliased edges onto a surface."""
    aapolygon(surface, points, color)
    filled_polygon(surface, points, color)


def sign(n):
    """Return the sign of number n."""
    return -1 if n < 0 else 1 if n else 0


def cosin(x):
    """Return the sum of cosine and sine of x (measured in radians)."""
    return cos(x) + sin(x)


def choices(d):
    """Choose a random key from a dict which has values being relative
    weights of the coresponding keys.
    """
    population, weights = tuple(d.keys()), tuple(d.values())
    cum_weights = [weights[0]]
    for weight in weights[1:]: cum_weights.append(cum_weights[-1] + weight)
    num = uniform(0, cum_weights[-1])
    for i, w in enumerate(cum_weights):
        if num <= w: return population[i]
