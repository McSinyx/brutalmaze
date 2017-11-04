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
from math import atan, atan2, sin, pi
from random import choice, shuffle, uniform

import pygame

from .constants import *
from .utils import sign, cosin, randsign, regpoly, fill_aapolygon
from .weapons import Bullet


class Hero:
    """Object representing the hero.

    Attributes:
        surface (pygame.Surface): the display to draw on
        x, y (int): coordinates of the center of the hero (in pixels)
        angle (float): angle of the direction the hero pointing (in radians)
        color (tuple of pygame.Color): colors of the hero on different HPs
        R (int): circumradius of the regular triangle representing the hero
        next_strike (int): the tick that the hero can do the next attack
        slashing (bool): flag indicates if the hero is doing close-range attack
        firing (bool): flag indicates if the hero is doing long-range attack
        dead (bool): flag indicates if the hero is dead
        spin_speed (float): speed of spinning (in frames per slash)
        spin_queue (float): frames left to finish spinning
        wound (float): amount of wound
    """
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
    """Object representing an enemy.

    Attributes:
        maze (Maze): the maze
        x, y (int): coordinates of the center of the enemy (in grids)
        angle (float): angle of the direction the enemy pointing (in radians)
        color (tuple of pygame.Color): colors of the enemy on different HPs
        awake (bool): flag indicates if the enemy is active
        next_strike (int): the tick that the enemy can do the next attack
        move_speed (float): speed of movement (in frames per grid)
        offsetx, offsety (integer): steps moved from the center of the grid
        spin_speed (float): speed of spinning (in frames per slash)
        spin_queue (float): frames left to finish spinning
        wound (float): amount of wound
    """
    def __init__(self, maze, x, y):
        self.maze = maze
        self.x, self.y = x, y
        self.maze.map[x][y] = ENEMY
        self.angle, self.color = pi / 4, TANGO[choice(ENEMIES)]

        self.awake = False
        self.next_strike = 0
        self.move_speed = self.maze.fps / ENEMY_SPEED
        self.offsetx = self.offsety = 0
        self.spin_speed = self.maze.fps / ENEMY_HP
        self.spin_queue = self.wound = 0.0

    def pos(self):
        """Return coordinate of the center of the enemy."""
        x, y = self.maze.pos(self.x, self.y)
        step = self.maze.distance * HERO_SPEED / self.maze.fps
        return x + self.offsetx*step, y + self.offsety*step

    def place(self, x=0, y=0):
        """Move the enemy by (x, y) (in grids)."""
        self.x += x
        self.y += y
        self.maze.map[self.x][self.y] = ENEMY

    def wake(self):
        """Wake the enemy up if it can see the hero."""
        if self.awake: return
        startx = starty = MIDDLE
        stopx, stopy, distance = self.x, self.y, self.maze.distance
        if startx > stopx: startx, stopx = stopx, startx
        if starty > stopy: starty, stopy = stopy, starty
        dx = (self.x-MIDDLE)*distance + self.maze.centerx - self.maze.x
        dy = (self.y-MIDDLE)*distance + self.maze.centery - self.maze.y
        mind = cosin(abs(atan(dy / dx)) if dx else 0) * distance
        def length(x, y): return abs(dy*x - dx*y) / (dy**2 + dx**2)**0.5
        for i in range(startx, stopx + 1):
            for j in range(starty, stopy + 1):
                if self.maze.map[i][j] != WALL: continue
                x, y = self.maze.pos(i, j)
                if length(x - self.maze.x, y - self.maze.y) <= mind: return
        self.awake = True

    def fire(self):
        """Return True if the enemy shot the hero, False otherwise."""
        x, y = self.pos()
        if (self.maze.length(x, y) > FIRANGE*self.maze.distance
            or self.next_strike > pygame.time.get_ticks()
            or (self.x, self.y) in AROUND_HERO or self.offsetx or self.offsety
            or uniform(-2, 2) < (INIT_SCORE/self.maze.score) ** 2):
            return False
        self.next_strike = pygame.time.get_ticks() + ATTACK_SPEED
        self.maze.bullets.append(Bullet(
            self.maze.surface, x, y,
            atan2(self.maze.y - y, self.maze.x - x), self.color[0]))
        return True

    def move(self):
        """Handle the movement of the enemy.

        Return True if it moved, False otherwise.
        """
        if self.offsetx:
            self.offsetx -= sign(self.offsetx)
            return True
        if self.offsety:
            self.offsety -= sign(self.offsety)
            return True

        self.move_speed = self.maze.fps / ENEMY_SPEED
        directions = [(sign(MIDDLE - self.x), 0), (0, sign(MIDDLE - self.y))]
        shuffle(directions)
        directions.append(choice(CROSS))
        for x, y in directions:
            if (x or y) and self.maze.map[self.x + x][self.y + y] == EMPTY:
                self.offsetx = round(x * (1 - self.move_speed))
                self.offsety = round(y * (1 - self.move_speed))
                self.maze.map[self.x][self.y] = EMPTY
                self.place(x, y)
                return True
        return False

    def update(self):
        """Update the enemy."""
        if self.awake:
            self.spin_speed, old_speed = self.maze.fps / ENEMY_HP, self.spin_speed
            self.spin_queue *= self.spin_speed / old_speed
            if not self.spin_queue and not self.fire() and not self.move():
                self.spin_queue = randsign() * self.spin_speed
            if abs(self.spin_queue) > 0.5:
                self.angle += sign(self.spin_queue) * pi / 2 / self.spin_speed
                self.spin_queue -= sign(self.spin_queue)
            else:
                self.angle, self.spin_queue = pi / 4, 0.0
        radious = self.maze.distance/SQRT2 - self.awake*2
        square = regpoly(4, radious, self.angle, *self.pos())
        color = self.color[int(self.wound)] if self.awake else FG_COLOR
        fill_aapolygon(self.maze.surface, square, color)

    def hit(self, wound):
        """Handle the enemy when it's hit by a bullet."""
        self.wound += wound

    def die(self):
        """Handle the enemy's death."""
        self.maze.map[self.x][self.y] = EMPTY if self.awake else WALL
