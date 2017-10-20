# -*- coding: utf-8 -*-
# characters.py - module for hero and enemy classes
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

from collections import deque
from math import atan2, sin, pi
from random import shuffle

import pygame

from .constants import *
from .utils import randsign, regpoly, fill_aapolygon, pos, sign


class Hero:
    """Object representing the hero."""
    def __init__(self, surface, fps):
        self.surface = surface
        w, h = self.surface.get_width(), self.surface.get_height()
        self.x, self.y = w >> 1, h >> 1
        self.angle, self.color = pi / 4, TANGO['Aluminium']
        self.R = int((w * h / sin(pi*2/3) / 624) ** 0.5)

        self.spin_speed = int(round(fps / len(self.color)))
        self.spin_queue, self.slashing = deque(), False
        self.wound = 0.0

    def get_color(self):
        """Return the color of the hero based on the amount of wounds."""
        return self.color[int(self.wound)]

    def slash(self, hold=False):
        """Spin the hero. If the button is hold, delay before continue
        each spin.
        """
        if self.slashing and not self.spin_queue:
            if hold: self.spin_queue.extend([0] * (self.spin_speed >> 1))
            self.spin_queue.extend([randsign()] * self.spin_speed)

    def draw(self):
        """Draw the hero."""
        trigon = regpoly(3, self.R, self.angle, self.x, self.y)
        fill_aapolygon(self.surface, trigon, self.get_color())

    def update(self, fps):
        """Update the hero."""
        self.spin_speed = int(round(fps / (len(self.color)-self.wound)))
        self.wound -= HEAL_SPEED / len(self.color) / self.spin_speed
        if self.wound < 0: self.wound = 0.0

        self.slash(hold=True)
        direction = self.spin_queue.popleft() if self.spin_queue else 0
        if direction:
            self.angle += direction * pi * 2 / 3 / self.spin_speed
        else:
            # Follow the mouse cursor
            x, y = pygame.mouse.get_pos()
            self.angle = atan2(y - self.y, x - self.x)
        self.draw()

    def resize(self):
        """Resize the hero."""
        w, h = self.surface.get_width(), self.surface.get_height()
        self.x, self.y = w >> 1, h >> 1
        self.R = (w * h / sin(pi*2/3) / 624) ** 0.5


class Enemy:
    """Object representing an enemy."""
    def __init__(self, surface, fps, maze, kind, x, y):
        self.surface, self.maze = surface, maze
        self.angle, self.color = pi / 4, TANGO[kind]
        self.x, self.y = x, y
        self.maze[x][y] = ENEMY

        self.awake = False
        self.move_speed = fps / MOVE_SPEED
        self.offsetx = self.offsety = 0
        self.spin_speed = fps / len(self.color)
        self.spin_queue = self.wound = 0.0

    def pos(self, distance, middlex, middley):
        """Return coordinate of the center of the enemy."""
        x, y = pos(self.x, self.y, distance, middlex, middley)
        step = distance / self.move_speed
        return x + self.offsetx*step, y + self.offsety*step

    def draw(self, distance, middlex, middley):
        """Draw the enemy, given distance between grids and the middle grid."""
        radious = distance/SQRT2 - self.awake*2
        square = regpoly(4, radious, self.angle,
                         *self.pos(distance, middlex, middley))
        color = self.color[int(self.wound)] if self.awake else FG_COLOR
        fill_aapolygon(self.surface, square, color)

    def place(self, x=0, y=0):
        """Move the enemy by (x, y)."""
        self.x += x
        self.y += y
        self.maze[self.x][self.y] = ENEMY

    def move(self, fps):
        """Handle the movement of the enemy.

        Return True if it moved, False otherwise.
        """
        if self.offsetx:
            self.offsetx -= sign(self.offsetx)
            return True
        if self.offsety:
            self.offsety -= sign(self.offsety)
            return True

        self.move_speed = fps / MOVE_SPEED
        directions = [(sign(MIDDLE - self.x), 0), (0, sign(MIDDLE - self.y))]
        shuffle(directions)
        for x, y in directions:
            if (x or y) and self.maze[self.x + x][self.y + y] == EMPTY:
                self.offsetx = round(x * (1 - self.move_speed))
                self.offsety = round(y * (1 - self.move_speed))
                self.maze[self.x][self.y] = EMPTY
                self.place(x, y)
                return True
        return False

    def update(self, fps, distance, middlex, middley):
        """Update the enemy."""
        if self.awake:
            self.spin_speed, old_speed = fps / len(self.color), self.spin_speed
            self.spin_queue *= self.spin_speed / old_speed
            if not self.spin_queue and not self.move(fps):
                self.spin_queue = randsign() * self.spin_speed
            if abs(self.spin_queue) > 0.5:
                self.angle += sign(self.spin_queue) * pi / 2 / self.spin_speed
                self.spin_queue -= sign(self.spin_queue)
            else:
                self.angle, self.spin_queue = pi / 4, 0.0
        self.draw(distance, middlex, middley)

    def die(self):
        """Kill the enemy."""
        self.maze[self.x][self.y] = EMPTY if self.awake else WALL
