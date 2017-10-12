# -*- coding: utf-8 -*-
# characters.py - module containing objects representing heroes and enemies
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

from collections import deque
from math import atan2, cos, sin, pi

import pygame
from pygame.gfxdraw import filled_polygon, aapolygon

from .constants import *


def randsign():
    """Return either -1 or 1 (kind of) randomly."""
    return (pygame.time.get_ticks() & 1)*2 - 1


def regpoly(n, R, x, y, r):
    """Return the pointlist of the regular polygon with n sides,
    circumradius of R, the center point I(x, y) and one point A make the
    vector IA with angle r (in radians).
    """
    r %= pi * 2
    angles = [r + pi*2*side/n for side in range(n)]
    return [(x + R*cos(angle), y + R*sin(angle)) for angle in angles]


def fill_aapolygon(surface, points, color):
    """Draw a filled polygon with anti aliased edges onto a surface."""
    aapolygon(surface, points, BG_COLOR)
    filled_polygon(surface, points, color)


class Hero:
    """Object representing the hero."""
    def __init__(self, surface):
        self.surface = surface
        w, h = self.surface.get_width(), self.surface.get_height()
        self.x, self.y = w >> 1, h >> 1
        self.angle, self.color = pi / 4, TANGO['Aluminium']
        self.R = int((w * h / sin(pi*2/3) / 624) ** 0.5)

        self.wound = 0
        self.speed = FPS // len(self.color)
        self.spin_queue, self.slashing = deque(), False

    def resize(self):
        """Resize the hero."""
        w, h = self.surface.get_width(), self.surface.get_height()
        self.x, self.y = w >> 1, h >> 1
        self.R = int((w * h / sin(pi*2/3) / 624) ** 0.5)

    def slash(self, hold=False):
        """Spin the hero. If the button is hold, delay before continue
        each spin.
        """
        if self.slashing and not self.spin_queue:
            if hold: self.spin_queue.extend([0] * (self.speed >> 1))
            self.spin_queue.extend([randsign()] * self.speed)

    def draw(self, color=None):
        """Draw the hero."""
        trigon = regpoly(3, self.R, self.x, self.y, self.angle)
        fill_aapolygon(self.surface, trigon, color or self.color[self.wound])

    def update(self):
        """Update the hero."""
        self.slash(hold=True)
        direction = self.spin_queue.popleft() if self.spin_queue else 0
        self.draw(color=BG_COLOR)
        if direction:
            self.angle += direction * pi * 2 / 3 / self.speed
        else:
            # Follow the mouse cursor
            x, y = pygame.mouse.get_pos()
            self.angle = atan2(y - self.y, x - self.x)
        self.draw()


class Enemy:
    """Object representing an enemy."""
    def __init__(self, surface, n, x, y):
        self.surface = surface
        self.x, self.y = x, y
        self.angle, self.color = pi / 4, TANGO[TANGO_KEYS[n]]

        self.moving = False
        self.wound = 0
        self.speed = FPS // len(self.color)
        self.spin_queue, self.slashing = deque(), False

    def draw(self, distance, middlex, middley, color=None):
        """Draw the enemy, given distance between blocks and the middle
        block.
        """
        x = middlex + (self.x - MIDDLE)*distance
        y = middley + (self.y - MIDDLE)*distance
        square = regpoly(4, int(distance / SQRT2), x, y, self.angle)
        fill_aapolygon(self.surface, square, color or self.color[self.wound])

    def update(self, distance, middlex, middley):
        """Update the enemy."""
        if (self.angle - pi/4) < FLOATING_ZERO: self.angle = pi / 4
        self.draw(distance, middlex, middley, color=BG_COLOR)
        if not self.spin_queue:
            self.spin_queue.extend([randsign()] * self.speed)
        if self.spin_queue and not self.moving:
            self.angle += self.spin_queue.popleft() * pi / 2 / self.speed
        self.draw(distance, middlex, middley)

    def place(self, x, y):
        """Move the enemy by (x, y)."""
        self.x += x
        self.y += y

    def move(self, x, y):
        """Command the enemy to move by (x, y)."""
