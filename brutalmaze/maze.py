# -*- coding: utf-8 -*-
# maze.py - module for the maze class
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
from math import pi, atan, cos, sin, log
from random import choice, getrandbits

import pygame

from .characters import pos, sign, regpoly, fill_aapolygon, Hero, Enemy
from .constants import *

__doc__ = 'brutalmaze module for the maze class'


def cosin(x):
    """Return the sum of cosine and sine of x (measured in radians)."""
    return cos(x) + sin(x)


def length(x0, y0, x1, y1):
    """Return the length of the line segment joining the two points
    (x0, y0) and (x1, y1).
    """
    return ((x0-x1)**2 + (y0-y1)**2)**0.5


def cell(bit, upper=True):
    """Return a half of a cell of the maze based on the given bit."""
    if bit: return deque([WALL]*ROAD_WIDTH + [EMPTY]*ROAD_WIDTH)
    if upper: return deque([WALL] * (ROAD_WIDTH<<1))
    return deque([EMPTY] * (ROAD_WIDTH<<1))


def new_column():
    """Return a newly generated column of the maze."""
    column = deque()
    upper, lower = deque(), deque()
    for _ in range(MAZE_SIZE):
        b = getrandbits(1)
        upper.extend(cell(b))
        lower.extend(cell(b, False))
    for _ in range(ROAD_WIDTH): column.append(upper.__copy__())
    for _ in range(ROAD_WIDTH): column.append(lower.__copy__())
    return column


class Maze:
    """Object representing the maze, including the characters."""
    def __init__(self, size):
        self.w, self.h = size
        self.surface = pygame.display.set_mode(size, RESIZABLE)
        self.distance = (self.w * self.h / 416) ** 0.5
        self.step = self.distance / MOVE_SPEED
        self.middlex, self.middley = self.x, self.y = self.w >> 1, self.h >> 1
        w, h = (int((i/self.distance+2) / 2) for i in size)
        self.rangex = range(MIDDLE - w, MIDDLE + w + 1)
        self.rangey = range(MIDDLE - h, MIDDLE + h + 1)
        self.right = self.down = self.offsetx = self.offsety = 0
        self.score = INIT_SCORE

        self.map = deque()
        for _ in range(MAZE_SIZE): self.map.extend(new_column())
        self.rotatex = self.rotatey = 0
        self.enemies = []
        self.add_enemy()
        self.hero = Hero(self.surface)
        self.map[MIDDLE][MIDDLE] = HERO
        self.slashd = self.hero.R + self.distance/SQRT2
        self.draw()

    def add_enemy(self):
        """Add enough enemies."""
        walls, length = [], log(self.score, GOLDEN_MEAN)
        for i in self.rangex:
            for j in self.rangey:
                if self.map[i][j] == WALL: walls.append((i, j))
        while walls and len(self.enemies) < length:
            x, y = choice(walls)
            if all(self.map[x + a][y + b] == WALL for a, b in ADJACENT_GRIDS):
                continue
            self.enemies.append(
                Enemy(self.surface, self.map, choice(ENEMIES), x, y))
            walls.remove((x, y))

    def draw(self):
        """Draw the maze."""
        self.surface.fill(BG_COLOR)
        for i in self.rangex:
            for j in self.rangey:
                if self.map[i][j] != WALL: continue
                x, y = pos(i, j, self.distance, self.middlex, self.middley)
                square = regpoly(4, self.distance / SQRT2, pi / 4, x, y)
                fill_aapolygon(self.surface, square, FG_COLOR)

    def wake(self, enemy):
        """Wake the enemy up if it can see the hero."""
        dx = (enemy.x - MIDDLE)*self.distance + self.offsetx*self.step
        dy = (enemy.y - MIDDLE)*self.distance + self.offsety*self.step
        mind = cosin(abs(atan(dy / dx)) if dx else 0) * self.distance
        startx = starty = MIDDLE
        stopx, stopy = enemy.x, enemy.y
        if startx > stopx : startx, stopx = stopx, startx
        if starty > stopy : starty, stopy = stopy, starty
        for i in range(startx, stopx + 1):
            for j in range(starty, stopy + 1):
                if self.map[i][j] != WALL: continue
                x, y = pos(i, j, self.distance, self.middlex, self.middley)
                d = abs(dy*(x-self.x) - dx*(y-self.y)) / (dy**2 + dx**2)**0.5
                if d <= mind: return
        enemy.awake = True

    def rotate(self, x, y):
        """Rotate the maze by (x, y)."""
        for enemy in self.enemies: self.map[enemy.x][enemy.y] = EMPTY
        if x:
            self.offsetx = 0
            self.map.rotate(x)
            self.rotatex += x
        if y:
            self.offsety = 0
            for d in self.map: d.rotate(y)
            self.rotatey += y

        # Respawn the enemies that fall off the display
        killist = []
        for i, enemy in enumerate(self.enemies):
            enemy.place(x, y)
            if enemy.x not in self.rangex or enemy.y not in self.rangey:
                enemy.die()
                killist.append(i)
        for i in reversed(killist): self.enemies.pop(i)
        self.add_enemy()

        # Regenerate the maze
        if abs(self.rotatex) == CELL_WIDTH:
            self.rotatex = 0
            for _ in range(CELL_WIDTH): self.map.pop()
            self.map.extend(new_column())
            for i in range(-CELL_WIDTH, 0):
                self.map[i].rotate(self.rotatey)
        if abs(self.rotatey) == CELL_WIDTH:
            self.rotatey = 0
            for i in range(MAZE_SIZE):
                b, c = getrandbits(1), (i-1)*CELL_WIDTH + self.rotatex
                for j, grid in enumerate(cell(b)):
                    for k in range(ROAD_WIDTH):
                        self.map[c + k][LAST_ROW + j] = grid
                c += ROAD_WIDTH
                for j, grid in enumerate(cell(b, False)):
                    for k in range(ROAD_WIDTH):
                        self.map[c + k][LAST_ROW + j] = grid

    def slash(self):
        """Slash the enemies."""
        unit, killist = self.distance/SQRT2 * self.hero.speed, []
        for i, enemy in enumerate(self.enemies):
            x, y = enemy.pos(self.distance, self.middlex, self.middley)
            d = length(x, y, self.x, self.y)
            if d <= self.slashd:
                enemy.wound += (self.slashd-d) / unit
                if enemy.wound >= len(enemy.color):
                    self.score += enemy.wound
                    enemy.die()
                    killist.append(i)
        for i in reversed(killist): self.enemies.pop(i)
        self.add_enemy()

    def update(self):
        """Update the maze."""
        modified, d = False, self.distance*1.5 - self.hero.R
        self.offsetx += self.right
        s = sign(self.offsetx) * 2
        if ((self.map[MIDDLE - s][MIDDLE - 1]
             or self.map[MIDDLE - s][MIDDLE]
             or self.map[MIDDLE - s][MIDDLE + 1])
            and abs(self.offsetx*self.step) > d):
            self.offsetx -= self.right
        else:
            modified = True

        self.offsety += self.down
        s = sign(self.offsety) * 2
        if ((self.map[MIDDLE - 1][MIDDLE - s]
             or self.map[MIDDLE][MIDDLE - s]
             or self.map[MIDDLE + 1][MIDDLE - s])
            and abs(self.offsety*self.step) > d):
            self.offsety -= self.down
        else:
            modified = True

        if modified:
            self.map[MIDDLE][MIDDLE] = EMPTY
            self.rotate(sign(self.offsetx) * (abs(self.offsetx)==MOVE_SPEED),
                        sign(self.offsety) * (abs(self.offsety)==MOVE_SPEED))
            self.map[MIDDLE][MIDDLE] = HERO
            self.middlex = self.x + self.offsetx*self.step
            self.middley = self.y + self.offsety*self.step
            self.draw()
            for enemy in self.enemies:
                if not enemy.awake: self.wake(enemy)

        for enemy in self.enemies:
            enemy.update(self.distance, self.middlex, self.middley)
        self.hero.update()
        if self.hero.slashing: self.slash()
        for enemy in self.enemies:
            if not enemy.spin_queue: continue
            x, y = enemy.pos(self.distance, self.middlex, self.middley)
            d = length(x, y, self.x, self.y)
            if d <= self.slashd:
                self.hero.wound += (self.slashd-d) / self.hero.R / enemy.speed
        pygame.display.flip()
        pygame.display.set_caption('Brutal Maze - Score: {}'.format(
            int(self.score - INIT_SCORE)))
        if self.hero.wound + 1 > len(self.hero.color): self.lose()

    def resize(self, w, h):
        """Resize the maze."""
        size = self.w, self.h = w, h
        self.surface = pygame.display.set_mode(size, RESIZABLE)
        self.hero.resize()

        self.distance = (w * h / 416) ** 0.5
        self.step = self.distance / MOVE_SPEED
        self.middlex = self.x + self.offsetx*self.step
        self.middley = self.y + self.offsety*self.step
        self.x, self.y = w >> 1, h >> 1
        w, h = int((w/self.distance+2) / 2), int((h/self.distance+2) / 2)
        self.rangex = range(MIDDLE - w, MIDDLE + w + 1)
        self.rangey = range(MIDDLE - h, MIDDLE + h + 1)
        self.draw()

    def move(self, x, y):
        """Command the maze to move x step/frame faster to the left and
        y step/frame faster upward so the hero will move in the reverse
        direction.
        """
        self.right += x
        self.down += y
        self.right, self.down = sign(self.right), sign(self.down)

    def lose(self):
        """Handle loses."""
        quit()
