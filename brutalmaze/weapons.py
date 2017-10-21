# -*- coding: utf-8 -*-
# characters.py - module for weapon classes
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

__doc__ = 'brutalmaze module for weapon classes'

from math import pi, cos, sin

from pygame.time import get_ticks

from .constants import *
from .utils import randsign, regpoly, fill_aapolygon, pos, sign


class Bullet:
    """Object representing a bullet."""
    def __init__(self, surface, x, y, angle, color):
        self.surface = surface
        self.x, self.y, self.angle, self.color = x, y, angle, color
        self.fall_time = get_ticks() + BULLET_LIFETIME

    def update(self, fps, distance):
        """Update the bullet."""
        s = distance * BULLET_SPEED / fps
        self.x += s * cos(self.angle)
        self.y += s * sin(self.angle)
        hexagon = regpoly(5, distance // 4, self.angle, self.x, self.y)
        fill_aapolygon(self.surface, hexagon, self.color)

    def place(self, x, y, step):
        """Move the bullet by (x, y) (in steps)."""
        self.x += x * step
        self.y += y * step
