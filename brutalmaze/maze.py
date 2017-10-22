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
from math import pi, atan, atan2, log
from random import choice, getrandbits, uniform

import pygame
from pygame import RESIZABLE

from .characters import Hero, Enemy
from .constants import *
from .utils import round2, pos, sign, cosin, length, regpoly, fill_aapolygon
from .weapons import Bullet

__doc__ = 'brutalmaze module for the maze class'


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
    def __init__(self, size, fps):
        self.w, self.h = size
        self.fps, self.speed = fps, fps / MOVE_SPEED
        self.surface = pygame.display.set_mode(size, RESIZABLE)
        self.distance = (self.w * self.h / 416) ** 0.5
        self.step = self.distance / self.speed
        self.middlex, self.middley = self.x, self.y = self.w >> 1, self.h >> 1
        w, h = (int(i/self.distance/2 + 2) for i in size)
        self.rangex = range(MIDDLE - w, MIDDLE + w + 1)
        self.rangey = range(MIDDLE - h, MIDDLE + h + 1)
        self.offsetx = self.offsety = 0.0
        self.paused, self.score = False, INIT_SCORE

        self.map = deque()
        for _ in range(MAZE_SIZE): self.map.extend(new_column())
        self.up = self.left = self.down = self.right = 0
        self.rotatex = self.rotatey = 0
        self.bullets, self.enemies = [], []
        self.add_enemy()
        self.hero = Hero(self.surface, fps)
        self.map[MIDDLE][MIDDLE] = HERO
        self.slashd = self.hero.R + self.distance/SQRT2

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
            self.enemies.append(Enemy(self.surface, self.fps, self.map, x, y))
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
        if not x and not y: return
        for enemy in self.enemies: self.map[enemy.x][enemy.y] = EMPTY

        if x:
            self.offsetx = 0.0
            self.map.rotate(x)
            self.rotatex += x
        if y:
            self.offsety = 0.0
            for d in self.map: d.rotate(y)
            self.rotatey += y

        # Respawn the enemies that fall off the display
        killist = []
        for i, enemy in enumerate(self.enemies):
            enemy.place(x, y)
            if enemy.x not in self.rangex or enemy.y not in self.rangey:
                self.score += enemy.wound
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
        """Handle close-ranged attacks."""
        for enemy in self.enemies:
            if not enemy.spin_queue: continue
            x, y = enemy.pos(self.distance, self.middlex, self.middley)
            d = self.slashd - length(x, y, self.x, self.y)
            if d >= 0:
                self.hero.wound += d / self.hero.R / enemy.spin_speed

        if not self.hero.spin_queue: return
        unit, killist = self.distance/SQRT2 * self.hero.spin_speed, []
        for i, enemy in enumerate(self.enemies):
            x, y = enemy.pos(self.distance, self.middlex, self.middley)
            d = length(x, y, self.x, self.y)
            if d <= self.slashd:
                enemy.wound += (self.slashd-d) / unit
                if enemy.wound >= ENEMY_HP:
                    self.score += enemy.wound
                    enemy.die()
                    killist.append(i)
        for i in reversed(killist): self.enemies.pop(i)
        self.add_enemy()

    def track_bullets(self):
        """Handle the bullets."""
        fallen, time = [], pygame.time.get_ticks()
        for enemy in self.enemies:
            # Chance that an enemy fire increase from 25% to 50%
            if uniform(-2, 2) > (INIT_SCORE/self.score)**2 and enemy.firable():
                x, y = enemy.pos(self.distance, self.middlex, self.middley)
                angle, color = atan2(self.y - y, self.x - x), enemy.color[0]
                self.bullets.append(Bullet(self.surface, x, y, angle, color))
        if (self.hero.firing and not self.hero.slashing
            and time >= self.hero.next_strike):
            self.hero.next_strike = time + ATTACK_SPEED
            self.bullets.append(Bullet(self.surface, self.x, self.y,
                                       self.hero.angle, FG_COLOR))
        for i, bullet in enumerate(self.bullets):
            wound = float(bullet.fall_time-time) / BULLET_LIFETIME
            bullet.update(self.fps, self.distance)
            if wound < 0:
                fallen.append(i)
            elif bullet.color == FG_COLOR:
                x = MIDDLE + round2((bullet.x-self.x) / self.distance)
                y = MIDDLE + round2((bullet.y-self.y) / self.distance)
                if self.map[x][y] == WALL:
                    fallen.append(i)
                    continue
                for j, enemy in enumerate(self.enemies):
                    x, y = enemy.pos(self.distance, self.middlex, self.middley)
                    if length(bullet.x, bullet.y, x, y) < self.distance:
                        enemy.wound += wound
                        if enemy.wound >= ENEMY_HP:
                            self.score += enemy.wound
                            enemy.die()
                            self.enemies.pop(j)
                        fallen.append(i)
                        break
            elif length(bullet.x, bullet.y, self.x, self.y) < self.distance:
                if not self.hero.spin_queue: self.hero.wound += wound
                fallen.append(i)
        for i in reversed(fallen): self.bullets.pop(i)

    def update(self, fps):
        """Update the maze."""
        if self.paused: return
        self.offsetx *= fps / self.fps
        self.offsety *= fps / self.fps
        self.fps, self.speed = fps, fps / MOVE_SPEED
        self.step = self.distance / self.speed

        d = self.distance*1.5 - self.hero.R
        dx, dy = sign(self.right) - sign(self.left), sign(self.down) - sign(self.up)
        self.offsetx += dx
        self.offsety += dy
        x, y = MIDDLE - sign(self.offsetx)*2, MIDDLE - sign(self.offsety)*2
        if ((self.map[x][MIDDLE - 1] != EMPTY
             or self.map[x][MIDDLE] != EMPTY
             or self.map[x][MIDDLE + 1] != EMPTY)
            and abs(self.offsetx*self.step) > d):
            self.offsetx -= dx
            dx = 0
        if ((self.map[MIDDLE - 1][y] != EMPTY
             or self.map[MIDDLE][y] != EMPTY
             or self.map[MIDDLE + 1][y] != EMPTY)
            and abs(self.offsety*self.step) > d):
            self.offsety -= dy
            dy = 0

        if dx or dy:
            self.map[MIDDLE][MIDDLE] = EMPTY
            self.rotate(sign(self.offsetx) * (abs(self.offsetx)>=self.speed),
                        sign(self.offsety) * (abs(self.offsety)>=self.speed))
            self.map[MIDDLE][MIDDLE] = HERO
            self.middlex = self.x + self.offsetx*self.step
            self.middley = self.y + self.offsety*self.step
            for enemy in self.enemies:
                if not enemy.awake: self.wake(enemy)
            for bullet in self.bullets: bullet.place(dx, dy, self.step)

        self.draw()
        for enemy in self.enemies:
            enemy.update(fps, self.distance, self.middlex, self.middley)
        self.hero.update(fps)
        self.slash()
        self.track_bullets()
        pygame.display.flip()
        pygame.display.set_caption('Brutal Maze - Score: {}'.format(
            int(self.score - INIT_SCORE)))
        if self.hero.wound + 1 > HERO_HP: self.lose()

    def resize(self, w, h):
        """Resize the maze."""
        size = self.w, self.h = w, h
        self.surface = pygame.display.set_mode(size, RESIZABLE)
        self.hero.resize()

        self.distance = (w * h / 416) ** 0.5
        self.step = self.distance / self.speed
        self.middlex = self.x + self.offsetx*self.step
        self.middley = self.y + self.offsety*self.step
        self.x, self.y = w >> 1, h >> 1
        w, h = int(w/self.distance/2 + 2), int(h/self.distance/2 + 2)
        self.rangex = range(MIDDLE - w, MIDDLE + w + 1)
        self.rangey = range(MIDDLE - h, MIDDLE + h + 1)
        self.slashd = self.hero.R + self.distance/SQRT2

    def move(self, up=0, left=0, down=0, right=0):
        """Make the maze to move in the given directions by moving the
        maze in the reverse way.
        """
        self.up += up
        self.left += left
        self.down += down
        self.right += right

    def lose(self):
        """Handle loses."""
        self.hero.die()
        self.up = self.left = self.down = self.right = 0
