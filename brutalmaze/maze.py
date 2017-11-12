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

__doc__ = 'brutalmaze module for the maze class'

from collections import deque
from math import pi, atan2, log
from random import choice, getrandbits

import pygame
from pygame import RESIZABLE

from .characters import Hero, new_enemy
from .constants import *
from .utils import round2, sign, regpoly, fill_aapolygon
from .weapons import Bullet


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
    """Object representing the maze, including the characters.

    Attributes:
        w, h: width and height of the display
        fps: current frame rate
        surface (pygame.Surface): the display to draw on
        distance (float): distance between centers of grids (in px)
        x, y (int): coordinates of the center of the hero (in px)
        centerx, centery (float): center grid's center's coordinates (in px)
        rangex, rangey: range of the index of the grids on display
        paused (bool): flag indicates if the game is paused
        score (float): current score
        map (deque of deque): map of grids representing objects on the maze
        vx, vy (float): velocity of the maze movement (in pixels per frame)
        rotatex, rotatey: grids rotated
        bullets (list of Bullet): bullets flying
        enemy_weights (dict): probabilities of enemies to be created
        enemies (list of Enemy): alive enemies
        hero (Hero): the hero
        slashd (float): minimum distance for slashes to be effective
    """
    def __init__(self, size, fps):
        self.w, self.h = size
        self.fps = fps
        self.surface = pygame.display.set_mode(size, RESIZABLE)
        self.distance = (self.w * self.h / 416) ** 0.5
        self.x, self.y = self.w // 2, self.h // 2
        self.centerx, self.centery = self.w / 2.0, self.h / 2.0
        w, h = (int(i/self.distance/2 + 2) for i in size)
        self.rangex = range(MIDDLE - w, MIDDLE + w + 1)
        self.rangey = range(MIDDLE - h, MIDDLE + h + 1)
        self.paused, self.score = False, INIT_SCORE

        self.map = deque()
        for _ in range(MAZE_SIZE): self.map.extend(new_column())
        self.vx = self.vy = 0.0
        self.rotatex = self.rotatey = 0
        self.bullets, self.enemies = [], []
        self.enemy_weights = {color: INIT_WEIGHT for color in ENEMIES}
        self.add_enemy()
        self.hero = Hero(self.surface, fps)
        self.map[MIDDLE][MIDDLE] = HERO
        self.slashd = self.hero.R + self.distance/SQRT2

    def add_enemy(self):
        """Add enough enemies."""
        walls = []
        for i in self.rangex:
            for j in self.rangey:
                if self.map[i][j] == WALL: walls.append((i, j))
        while walls and len(self.enemies) < log(self.score, INIT_SCORE):
            x, y = choice(walls)
            if all(self.map[x + a][y + b] == WALL for a, b in ADJACENT_GRIDS):
                continue
            self.enemies.append(new_enemy(self, x, y))
            walls.remove((x, y))

    def pos(self, x, y):
        """Return coordinate of the center of the grid (x, y)."""
        return (self.centerx + (x - MIDDLE)*self.distance,
                self.centery + (y - MIDDLE)*self.distance)

    def draw(self):
        """Draw the maze."""
        self.surface.fill(BG_COLOR)
        for i in self.rangex:
            for j in self.rangey:
                if self.map[i][j] != WALL: continue
                x, y = self.pos(i, j)
                square = regpoly(4, self.distance / SQRT2, pi / 4, x, y)
                fill_aapolygon(self.surface, square, FG_COLOR)

    def rotate(self):
        """Rotate the maze if needed."""
        x = int((self.centerx-self.x) * 2 / self.distance)
        y = int((self.centery-self.y) * 2 / self.distance)
        if x == y == 0: return
        for enemy in self.enemies: self.map[enemy.x][enemy.y] = EMPTY
        self.map[MIDDLE][MIDDLE] = EMPTY
        if x:
            self.centerx -= x * self.distance
            self.map.rotate(x)
            self.rotatex += x
        if y:
            self.centery -= y * self.distance
            for d in self.map: d.rotate(y)
            self.rotatey += y
        self.map[MIDDLE][MIDDLE] = HERO

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

    def length(self, x, y):
        """Return the length of the line segment joining the center of
        the maze and the point (x, y).
        """
        return ((self.x-x)**2 + (self.y-y)**2)**0.5

    def hit(self, wound, color):
        """Handle the hero when he loses HP."""
        self.hero.wound += wound
        self.enemy_weights[color] += wound

    def slash(self):
        """Handle close-range attacks."""
        for enemy in self.enemies:
            if not enemy.spin_queue: continue
            x, y = enemy.pos()
            d = self.slashd - self.length(x, y)
            if d >= 0:
                self.hit(d / self.hero.R / enemy.spin_speed, enemy.color)

        if not self.hero.spin_queue: return
        unit, killist = self.distance/SQRT2 * self.hero.spin_speed, []
        for i, enemy in enumerate(self.enemies):
            x, y = enemy.pos()
            d = self.length(x, y)
            if d <= self.slashd:
                enemy.hit((self.slashd-d) / unit)
                if enemy.wound >= ENEMY_HP:
                    self.score += enemy.wound
                    enemy.die()
                    killist.append(i)
        for i in reversed(killist): self.enemies.pop(i)
        self.add_enemy()

    def track_bullets(self):
        """Handle the bullets."""
        fallen, time = [], pygame.time.get_ticks()
        if (self.hero.firing and not self.hero.slashing
            and time >= self.hero.next_strike):
            self.hero.next_strike = time + ATTACK_SPEED
            self.bullets.append(Bullet(self.surface, self.x, self.y,
                                       self.hero.angle, 'Aluminium'))
        for i, bullet in enumerate(self.bullets):
            wound = float(bullet.fall_time-time) / BULLET_LIFETIME
            bullet.update(self.fps, self.distance)
            if wound < 0:
                fallen.append(i)
            elif bullet.color == 'Aluminium':
                x = MIDDLE + round2((bullet.x-self.x) / self.distance)
                y = MIDDLE + round2((bullet.y-self.y) / self.distance)
                if self.map[x][y] == WALL:
                    fallen.append(i)
                    continue
                for j, enemy in enumerate(self.enemies):
                    x, y = enemy.pos()
                    if bullet.length(x, y) < self.distance:
                        enemy.hit(wound)
                        if enemy.wound >= ENEMY_HP:
                            self.score += enemy.wound
                            enemy.die()
                            self.enemies.pop(j)
                        fallen.append(i)
                        break
            elif bullet.length(self.x, self.y) < self.distance:
                if not self.hero.spin_queue: self.hit(wound, bullet.color)
                fallen.append(i)
        for i in reversed(fallen): self.bullets.pop(i)

    def valid_move(self, vx=0.0, vy=0.0):
        """Return dx or dy if it it valid to move the maze in that
        velocity, otherwise return 0.0.
        """
        d = self.distance/2 + self.hero.R
        herox, heroy, dx, dy = self.x - vx, self.y - vy, sign(vx), sign(vy)
        for gridx in range(MIDDLE - dx - 1, MIDDLE - dx + 2):
            for gridy in range(MIDDLE - dy - 1, MIDDLE - dy + 2):
                x, y = self.pos(gridx, gridy)
                if (max(abs(herox - x), abs(heroy - y)) < d
                    and self.map[gridx][gridy] == WALL):
                    return 0.0
        for enemy in self.enemies:
            x, y = self.pos(enemy.x, enemy.y)
            if (max(abs(herox - x), abs(heroy - y)) * 2 < self.distance
                and enemy.awake):
                return 0.0
        return vx or vy

    def update(self, fps):
        """Update the maze."""
        if self.paused: return
        self.fps = fps
        dx = self.valid_move(vx=self.vx)
        self.centerx += dx
        dy = self.valid_move(vy=self.vy)
        self.centery += dy

        if dx or dy:
            self.rotate()
            for enemy in self.enemies: enemy.wake()
            for bullet in self.bullets: bullet.place(dx, dy)

        self.draw()
        for enemy in self.enemies: enemy.update()
        self.hero.update(fps)
        self.slash()
        self.track_bullets()
        pygame.display.flip()
        pygame.display.set_caption('Brutal Maze - Score: {}'.format(
            int(self.score - INIT_SCORE)))
        if self.hero.wound + 1 > HERO_HP: self.lose()

    def move(self, x, y, fps):
        """Command the hero to move faster in the given direction."""
        velocity = self.distance * HERO_SPEED / fps
        accel = velocity * HERO_SPEED / fps
        if not x:
            self.vx -= sign(self.vx) * accel
            if abs(self.vx) < accel * 2: self.vx = 0.0
        elif x * self.vx < 0:
            self.vx += x * 2 * accel
        else:
            self.vx += x * accel
            if abs(self.vx) > velocity: self.vx = x * velocity
        if not y:
            self.vy -= sign(self.vy) * accel
            if abs(self.vy) < accel * 2: self.vy = 0.0
        elif y * self.vy < 0:
            self.vy += y * 2 * accel
        else:
            self.vy += y * accel
            if abs(self.vy) > velocity: self.vy = y * velocity

    def resize(self, w, h):
        """Resize the maze."""
        size = self.w, self.h = w, h
        self.surface = pygame.display.set_mode(size, RESIZABLE)
        self.hero.resize()

        offsetx = (self.centerx-self.x) / self.distance
        offsety = (self.centery-self.y) / self.distance
        self.distance = (w * h / 416) ** 0.5
        self.x, self.y = w // 2, h // 2
        self.centerx = self.x + offsetx*self.distance
        self.centery = self.y + offsety*self.distance
        w, h = int(w/self.distance/2 + 2), int(h/self.distance/2 + 2)
        self.rangex = range(MIDDLE - w, MIDDLE + w + 1)
        self.rangey = range(MIDDLE - h, MIDDLE + h + 1)
        self.slashd = self.hero.R + self.distance/SQRT2

    def isfast(self):
        """Return if the hero is moving faster than HERO_SPEED."""
        return (self.vx**2+self.vy**2)**0.5*self.fps > HERO_SPEED*self.distance

    def lose(self):
        """Handle loses."""
        self.hero.die()
        self.vx = self.vy = 0.0
