# -*- coding: utf-8 -*-
# maze.py - module for the maze class
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

__doc__ = 'Brutal Maze module for the maze class'

from collections import deque
from math import pi, log
from random import choice, getrandbits, uniform

import pygame

from .characters import Hero, new_enemy
from .constants import (
    EMPTY, WALL, HERO, ROAD_WIDTH, MAZE_SIZE, MIDDLE, INIT_SCORE, ENEMIES,
    MINW, MAXW, SQRT2, SFX_SPAWN, SFX_SLASH_ENEMY, SFX_LOSE, ADJACENT_GRIDS,
    BG_COLOR, FG_COLOR, CELL_WIDTH, LAST_ROW, HERO_HP, ENEMY_HP, ATTACK_SPEED,
    HERO_SPEED, BULLET_LIFETIME)
from .misc import round2, sign, regpoly, fill_aapolygon, play
from .weapons import Bullet


def new_cell(bit, upper=True):
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
        upper.extend(new_cell(b))
        lower.extend(new_cell(b, False))
    for _ in range(ROAD_WIDTH): column.append(upper.__copy__())
    for _ in range(ROAD_WIDTH): column.append(lower.__copy__())
    return column


class Maze:
    """Object representing the maze, including the characters.

    Attributes:
        w, h (int): width and height of the display (in px)
        fps (float): current frame rate
        surface (pygame.Surface): the display to draw on
        distance (float): distance between centers of grids (in px)
        x, y (int): coordinates of the center of the hero (in px)
        centerx, centery (float): center grid's center's coordinates (in px)
        rangex, rangey (list): range of the index of the grids on display
        score (float): current score
        map (deque of deque): map of grids representing objects on the maze
        vx, vy (float): velocity of the maze movement (in pixels per frame)
        rotatex, rotatey (int): grids rotated
        bullets (list of Bullet): flying bullets
        enemy_weights (dict): probabilities of enemies to be created
        enemies (list of Enemy): alive enemies
        hero (Hero): the hero
        next_move (float): time until the hero gets mobilized (in ms)
        next_slashfx (float): time until next slash effect of the hero (in ms)
        slashd (float): minimum distance for slashes to be effective
        sfx_slash (pygame.mixer.Sound): sound effect of slashed enemy
        sfx_lose (pygame.mixer.Sound): sound effect to be played when you lose
    """
    def __init__(self, fps, size, scrtype, headless):
        self.fps = fps
        self.w, self.h = size
        self.scrtype = scrtype
        if headless:
            self.surface = None
        else:
            self.surface = pygame.display.set_mode(size, self.scrtype)

        self.distance = (self.w * self.h / 416) ** 0.5
        self.x, self.y = self.w // 2, self.h // 2
        self.centerx, self.centery = self.w / 2.0, self.h / 2.0
        w, h = (int(i/self.distance/2 + 1) for i in size)
        self.rangex = list(range(MIDDLE - w, MIDDLE + w + 1))
        self.rangey = list(range(MIDDLE - h, MIDDLE + h + 1))
        self.score = INIT_SCORE

        self.map = deque()
        for _ in range(MAZE_SIZE): self.map.extend(new_column())
        self.vx = self.vy = 0.0
        self.rotatex = self.rotatey = 0
        self.bullets, self.enemies = [], []
        self.enemy_weights = {color: MINW for color in ENEMIES}
        self.add_enemy()
        self.hero = Hero(self.surface, fps, size)
        self.map[MIDDLE][MIDDLE] = HERO
        self.next_move = self.next_slashfx = 0.0
        self.slashd = self.hero.R + self.distance/SQRT2

        self.sfx_spawn = SFX_SPAWN
        self.sfx_slash = SFX_SLASH_ENEMY
        self.sfx_lose = SFX_LOSE

    def add_enemy(self):
        """Add enough enemies."""
        walls = [(i, j) for i in self.rangex for j in self.rangey
                 if self.map[i][j] == WALL]
        plums = [e for e in self.enemies if e.color == 'Plum' and e.awake]
        plum = choice(plums) if plums else None
        num = log(self.score, INIT_SCORE)
        while walls and len(self.enemies) < num:
            x, y = choice(walls)
            if all(self.map[x + a][y + b] == WALL for a, b in ADJACENT_GRIDS):
                continue
            enemy = new_enemy(self, x, y)
            self.enemies.append(enemy)
            if plum is None or not plum.clone(enemy):
                walls.remove((x, y))
            else:
                self.map[x][y] = WALL

    def get_pos(self, x, y):
        """Return coordinate of the center of the grid (x, y)."""
        return (self.centerx + (x - MIDDLE)*self.distance,
                self.centery + (y - MIDDLE)*self.distance)

    def get_score(self):
        """Return the current score."""
        return int(self.score - INIT_SCORE)

    def draw(self):
        """Draw the maze."""
        self.surface.fill(BG_COLOR)
        if self.next_move <= 0:
            for i in self.rangex:
                for j in self.rangey:
                    if self.map[i][j] != WALL: continue
                    x, y = self.get_pos(i, j)
                    square = regpoly(4, self.distance / SQRT2, pi / 4, x, y)
                    fill_aapolygon(self.surface, square, FG_COLOR)

        for enemy in self.enemies: enemy.draw()
        if not self.hero.dead: self.hero.draw()
        bullet_radius = self.distance / 4
        for bullet in self.bullets: bullet.draw(bullet_radius)
        pygame.display.flip()
        pygame.display.set_caption(
            'Brutal Maze - Score: {}'.format(self.get_score()))

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
                for j, grid in enumerate(new_cell(b)):
                    for k in range(ROAD_WIDTH):
                        self.map[c + k][LAST_ROW + j] = grid
                c += ROAD_WIDTH
                for j, grid in enumerate(new_cell(b, False)):
                    for k in range(ROAD_WIDTH):
                        self.map[c + k][LAST_ROW + j] = grid

    def get_distance(self, x, y):
        """Return the distance from the center of the maze to the point
        (x, y).
        """
        return ((self.x-x)**2 + (self.y-y)**2)**0.5

    def hit_hero(self, wound, color):
        """Handle the hero when he loses HP."""
        fx = (uniform(0, sum(self.enemy_weights.values()))
              < self.enemy_weights[color])
        if (color == 'Butter' or color == 'ScarletRed') and fx:
            self.hero.wound += wound * 2.5
        elif color == 'Orange' and fx:
            self.hero.next_heal = max(self.hero.next_heal, 0) + wound*1000
        elif color == 'SkyBlue' and fx:
            self.next_move = max(self.next_move, 0) + wound*1000
        else:
            self.hero.wound += wound
        if self.enemy_weights[color] + wound < MAXW:
            self.enemy_weights[color] += wound
        if self.hero.wound > HERO_HP and not self.hero.dead: self.lose()

    def slash(self):
        """Handle close-range attacks."""
        for enemy in self.enemies: enemy.slash()
        if not self.hero.spin_queue: return
        killist = []
        for i, enemy in enumerate(self.enemies):
            d = self.slashd - enemy.get_distance()
            if d > 0:
                wound = d * SQRT2 / self.distance
                if self.next_slashfx <= 0:
                    play(self.sfx_slash, wound, enemy.get_angle())
                    self.next_slashfx = ATTACK_SPEED
                enemy.hit(wound / self.hero.spin_speed)
                if enemy.wound >= ENEMY_HP:
                    self.score += enemy.wound
                    enemy.die()
                    killist.append(i)
        for i in reversed(killist): self.enemies.pop(i)
        self.add_enemy()

    def track_bullets(self):
        """Handle the bullets."""
        fallen = []
        if (self.hero.firing and not self.hero.slashing
            and self.hero.next_strike <= 0):
            self.hero.next_strike = ATTACK_SPEED
            self.bullets.append(Bullet(self.surface, self.x, self.y,
                                       self.hero.angle, 'Aluminium'))
        for i, bullet in enumerate(self.bullets):
            wound = bullet.fall_time / BULLET_LIFETIME
            bullet.update(self.fps, self.distance)
            if wound < 0:
                fallen.append(i)
            elif bullet.color == 'Aluminium':
                x = MIDDLE + round2((bullet.x-self.x) / self.distance)
                y = MIDDLE + round2((bullet.y-self.y) / self.distance)
                if self.map[x][y] == WALL and self.next_move <= 0:
                    fallen.append(i)
                    continue
                for j, enemy in enumerate(self.enemies):
                    if not enemy.awake: continue
                    x, y = enemy.get_pos()
                    if bullet.get_distance(x, y) < self.distance:
                        enemy.hit(wound)
                        if enemy.wound >= ENEMY_HP:
                            self.score += enemy.wound
                            enemy.die()
                            self.enemies.pop(j)
                        play(bullet.sfx_hit, wound, bullet.angle)
                        fallen.append(i)
                        break
            elif bullet.get_distance(self.x, self.y) < self.distance:
                if self.hero.spin_queue and self.hero.next_heal <= 0:
                    self.hero.next_strike = (abs(self.hero.spin_queue*self.fps)
                                             + ATTACK_SPEED)
                    play(bullet.sfx_missed, wound, bullet.angle + pi)
                else:
                    self.hit_hero(wound, bullet.color)
                    play(bullet.sfx_hit, wound, bullet.angle + pi)
                fallen.append(i)
        for i in reversed(fallen): self.bullets.pop(i)

    def is_valid_move(self, vx=0.0, vy=0.0):
        """Return dx or dy if it it valid to move the maze in that
        velocity, otherwise return 0.0.
        """
        d = self.distance/2 + self.hero.R
        herox, heroy, dx, dy = self.x - vx, self.y - vy, sign(vx), sign(vy)
        for gridx in range(MIDDLE - dx - 1, MIDDLE - dx + 2):
            for gridy in range(MIDDLE - dy - 1, MIDDLE - dy + 2):
                x, y = self.get_pos(gridx, gridy)
                if (max(abs(herox - x), abs(heroy - y)) < d
                    and self.map[gridx][gridy] == WALL):
                    return 0.0
        for enemy in self.enemies:
            x, y = self.get_pos(enemy.x, enemy.y)
            if (max(abs(herox - x), abs(heroy - y)) * 2 < self.distance
                and enemy.awake):
                return 0.0
        return vx or vy

    def update(self, fps):
        """Update the maze."""
        self.fps = fps
        dx = self.is_valid_move(vx=self.vx)
        self.centerx += dx
        dy = self.is_valid_move(vy=self.vy)
        self.centery += dy

        self.next_move -= 1000.0 / self.fps
        self.next_slashfx -= 1000.0 / self.fps

        if dx or dy:
            self.rotate()
            for enemy in self.enemies: enemy.wake()
            for bullet in self.bullets: bullet.place(dx, dy)

        for enemy in self.enemies: enemy.update()
        if not self.hero.dead:
            self.hero.update(fps)
            self.slash()
        self.track_bullets()

    def resize(self, size):
        """Resize the maze."""
        self.w, self.h = size
        self.surface = pygame.display.set_mode(size, self.scrtype)
        self.hero.resize(size)

        offsetx = (self.centerx-self.x) / self.distance
        offsety = (self.centery-self.y) / self.distance
        self.distance = (self.w * self.h / 416) ** 0.5
        self.x, self.y = self.w // 2, self.h // 2
        self.centerx = self.x + offsetx*self.distance
        self.centery = self.y + offsety*self.distance
        w, h = int(self.w/self.distance/2 + 1), int(self.h/self.distance/2 + 1)
        self.rangex = list(range(MIDDLE - w, MIDDLE + w + 1))
        self.rangey = list(range(MIDDLE - h, MIDDLE + h + 1))
        self.slashd = self.hero.R + self.distance/SQRT2

    def isfast(self):
        """Return if the hero is moving faster than HERO_SPEED."""
        return (self.vx**2+self.vy**2)**0.5*self.fps > HERO_SPEED*self.distance

    def lose(self):
        """Handle loses."""
        self.hero.dead = True
        self.hero.slashing = self.hero.firing = False
        self.vx = self.vy = 0.0
        play(self.sfx_lose)

    def reinit(self):
        """Open new game."""
        self.centerx, self.centery = self.w / 2.0, self.h / 2.0
        self.score = INIT_SCORE
        self.map = deque()
        for _ in range(MAZE_SIZE): self.map.extend(new_column())
        self.vx = self.vy = 0.0
        self.rotatex = self.rotatey = 0
        self.bullets, self.enemies = [], []
        self.enemy_weights = {color: MINW for color in ENEMIES}
        self.add_enemy()

        self.next_move = self.next_slashfx = 0.0
        self.hero.next_heal = self.hero.next_strike = 0
        self.hero.slashing = self.hero.firing = self.hero.dead = False
        self.hero.spin_queue = self.hero.wound = 0.0
