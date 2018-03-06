# -*- coding: utf-8 -*-
# characters.py - module for weapon classes
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

__doc__ = 'Brutal Maze module for weapon classes'

from math import cos, sin

from .constants import (BULLET_LIFETIME, SFX_SHOT_ENEMY, SFX_SHOT_HERO,
                        SFX_MISSED, BULLET_SPEED, ENEMY_HP, TANGO, BG_COLOR)
from .misc import regpoly, fill_aapolygon


class Bullet:
    """Object representing a bullet.

    Attributes:
        surface (pygame.Surface): the display to draw on
        x, y (int): coordinates of the center of the bullet (in pixels)
        angle (float): angle of the direction the bullet pointing (in radians)
        color (str): bullet's color name
        fall_time (int): time until the bullet fall down
        sfx_hit (pygame.mixer.Sound): sound effect indicating target was hit
        sfx_missed (pygame.mixer.Sound): sound effect indicating a miss shot
    """
    def __init__(self, surface, x, y, angle, color):
        self.surface = surface
        self.x, self.y, self.angle, self.color = x, y, angle, color
        self.fall_time = BULLET_LIFETIME
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
        self.fall_time -= 1000.0 / fps

    def get_color(self):
        """Return current color of the enemy."""
        value = int((1 - self.fall_time/BULLET_LIFETIME) * ENEMY_HP)
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
