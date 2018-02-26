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

from math import cos, sin

from pygame.time import get_ticks

from .constants import *
from .misc import regpoly, fill_aapolygon


class Bullet:
    """Object representing a bullet.

    Attributes:
        surface (pygame.Surface): the display to draw on
        x, y (int): coordinates of the center of the bullet (in pixels)
        angle (float): angle of the direction the bullet pointing (in radians)
        color (str): bullet's color name
        fall_time (int): the tick that the bullet will fall down
        sfx_hit (pygame.mixer.Sound): sound effect indicating target was hit
        sfx_missed (pygame.mixer.Sound): sound effect indicating a miss shot
    """
    def __init__(self, surface, x, y, angle, color):
        self.surface = surface
        self.x, self.y, self.angle, self.color = x, y, angle, color
        self.fall_time = get_ticks() + BULLET_LIFETIME
        if color == 'Aluminium':
            self.sfx_hit = SFX_SHOT_ENEMY
        else:
            self.sfx_hit = SFX_SHOT_HERO
        self.sfx_missed = SFX_MISSED

    def update(self, fps, distance):
        """Update the bullet."""
        s = distance * BULLET_SPEED / fps
        self.x += s * cos(self.angle)
        self.y += s * sin(self.angle)

    def get_color(self):
        """Return current color of the enemy."""
        value = int((1-(self.fall_time-get_ticks())/BULLET_LIFETIME)*ENEMY_HP)
        try:
            return TANGO[self.color][value]
        except IndexError:
            return BG_COLOR

    def draw(self, radius):
        """Draw the bullet."""
        pentagon = regpoly(5, radius, self.angle, self.x, self.y)
        fill_aapolygon(self.surface, pentagon, self.get_color())

    def place(self, x, y):
        """Move the bullet by (x, y) (in pixels)."""
        self.x += x
        self.y += y

    def get_distance(self, x, y):
        """Return the from the center of the bullet to the point (x, y)."""
        return ((self.x-x)**2 + (self.y-y)**2)**0.5
