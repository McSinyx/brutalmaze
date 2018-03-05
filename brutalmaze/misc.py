# -*- coding: utf-8 -*-
# misc.py - module for miscellaneous functions
# Copyright (C) 2017, 2018  Nguyễn Gia Phong
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

from math import degrees, cos, sin, pi
from random import uniform

import pygame
from pygame.gfxdraw import filled_polygon, aapolygon


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


def deg(x):
    """Convert angle x from radians to degrees casted to a nonnegative
    integer.
    """
    return round2((lambda a: a if a > 0 else a + 360)(degrees(x)))


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


def play(sound, volume=1.0, angle=None):
    """Play a pygame.mixer.Sound at the given volume."""
    if pygame.mixer.get_init() is None: return
    if pygame.mixer.find_channel() is None:
        pygame.mixer.set_num_channels(pygame.mixer.get_num_channels() + 1)

    channel = sound.play()
    if angle is None:
        channel.set_volume(volume)
    else:
        delta = cos(angle)
        volumes = [volume * (1-delta), volume * (1+delta)]
        for i, v in enumerate(volumes):
            if v > 1:
                volumes[i - 1] += v - 1
                volumes[i] = 1.0
        sound.set_volume(1.0)
        channel.set_volume(*volumes)
