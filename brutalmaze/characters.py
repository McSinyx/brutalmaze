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

from collections import deque
from math import atan2, sin, pi
from random import choice, shuffle

import pygame

from .constants import *
from .utils import randsign, regpoly, fill_aapolygon, pos, sign

__doc__ = 'brutalmaze module for hero and enemy classes'


class Hero:
    """Object representing the hero."""
    def __init__(self, surface, fps):
        self.surface = surface
        w, h = self.surface.get_width(), self.surface.get_height()
        self.x, self.y = w >> 1, h >> 1
        self.angle, self.color = pi / 4, TANGO['Aluminium']
        self.R = int((w * h / sin(pi*2/3) / 624) ** 0.5)

        self.next_strike = 0
        self.slashing = self.firing = self.dead = False
        self.spin_speed = fps / HERO_HP
        self.spin_queue = self.wound = 0.0

    def update(self, fps):
        """Update the hero."""
        old_speed, time = self.spin_speed, pygame.time.get_ticks()
        self.spin_speed = fps / (HERO_HP-self.wound**0.5)
        self.spin_queue *= self.spin_speed / old_speed
        if not self.dead: self.wound -= HEAL_SPEED / self.spin_speed / HERO_HP
        if self.wound < 0: self.wound = 0.0

        if self.slashing and time >= self.next_strike:
            self.next_strike = time + ATTACK_SPEED
            self.spin_queue = randsign() * self.spin_speed
        if abs(self.spin_queue) > 0.5:
            self.angle += sign(self.spin_queue) * pi / 2 / self.spin_speed
            self.spin_queue -= sign(self.spin_queue)
        else:
            # Follow the mouse cursor
            x, y = pygame.mouse.get_pos()
            self.angle = atan2(y - self.y, x - self.x)
            self.spin_queue = 0.0
        trigon = regpoly(3, self.R, self.angle, self.x, self.y)
        try:
            fill_aapolygon(self.surface, trigon, self.color[int(self.wound)])
        except IndexError:  # When the hero is wounded over his HP
            self.wound = HERO_HP

    def die(self):
        """Handle the hero's death."""
        self.dead = True
        self.slashing = self.firing = False

    def resize(self):
        """Resize the hero."""
        w, h = self.surface.get_width(), self.surface.get_height()
        self.x, self.y = w >> 1, h >> 1
        self.R = (w * h / sin(pi*2/3) / 624) ** 0.5


class Enemy:
    """Object representing an enemy."""
    def __init__(self, surface, fps, maze, x, y):
        self.surface, self.maze = surface, maze
        self.angle, self.color = pi / 4, TANGO[choice(ENEMIES)]
        self.x, self.y = x, y
        self.maze[x][y] = ENEMY

        self.awake = False
        self.next_move = 0
        self.move_speed = fps / MOVE_SPEED
        self.offsetx = self.offsety = 0
        self.spin_speed = fps / ENEMY_HP
        self.spin_queue = self.wound = 0.0

    def pos(self, distance, middlex, middley):
        """Return coordinate of the center of the enemy."""
        x, y = pos(self.x, self.y, distance, middlex, middley)
        step = distance / self.move_speed
        return x + self.offsetx*step, y + self.offsety*step

    def place(self, x=0, y=0):
        """Move the enemy by (x, y) (in grids)."""
        self.x += x
        self.y += y
        self.maze[self.x][self.y] = ENEMY

    def move(self, fps):
        """Handle the movement of the enemy.

        Return True if it moved, False otherwise.
        """
        if self.next_move > pygame.time.get_ticks(): return False
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
            self.spin_speed, old_speed = fps / ENEMY_HP, self.spin_speed
            self.spin_queue *= self.spin_speed / old_speed
            if not self.spin_queue and not self.move(fps):
                self.spin_queue = randsign() * self.spin_speed
            if abs(self.spin_queue) > 0.5:
                self.angle += sign(self.spin_queue) * pi / 2 / self.spin_speed
                self.spin_queue -= sign(self.spin_queue)
            else:
                self.angle, self.spin_queue = pi / 4, 0.0
        radious = distance/SQRT2 - self.awake*2
        square = regpoly(4, radious, self.angle,
                         *self.pos(distance, middlex, middley))
        color = self.color[int(self.wound)] if self.awake else FG_COLOR
        fill_aapolygon(self.surface, square, color)

    def firable(self):
        """Return True if the enemies should shoot the hero,
        False otherwise.
        """
        if (not self.awake or self.spin_queue or self.offsetx or self.offsety
            or (self.x, self.y) in SURROUND_HERO):
            return False
        self.next_move = pygame.time.get_ticks() + ATTACK_SPEED
        return True

    def die(self):
        """Handle the enemy's death."""
        self.maze[self.x][self.y] = EMPTY if self.awake else WALL
