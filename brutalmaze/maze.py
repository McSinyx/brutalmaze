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

from collections import defaultdict, deque
import json
from math import pi, log
from os import path
from random import choice, sample, uniform

import pygame

from .characters import Hero, new_enemy
from .constants import (
    EMPTY, WALL, HERO, ENEMY, ROAD_WIDTH, WALL_WIDTH, CELL_WIDTH, CELL_NODES,
    MAZE_SIZE, MIDDLE, INIT_SCORE, ENEMIES, MINW, MAXW, SQRT2, SFX_SPAWN,
    SFX_SLASH_ENEMY, SFX_LOSE, ADJACENTS, TANGO_VALUES, BG_COLOR, FG_COLOR,
    COLORS, HERO_HP, ENEMY_HP, ATTACK_SPEED, MAX_WOUND, HERO_SPEED,
    BULLET_LIFETIME, JSON_SEPARATORS)
from .misc import (
    round2, sign, deg, around, regpoly, fill_aapolygon, play, json_rec)
from .weapons import LockOn


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
        bullets (list of .weapons.Bullet): flying bullets
        enemy_weights (dict): probabilities of enemies to be created
        enemies (list of Enemy): alive enemies
        hero (Hero): the hero
        destx, desty (int): the grid the hero is moving to
        stepx, stepy (int): direction the maze is moving
        target (Enemy or LockOn): target to automatically aim at
        next_move (float): time until the hero gets mobilized (in ms)
        glitch (float): time that the maze remain flashing colors (in ms)
        next_slashfx (float): time until next slash effect of the hero (in ms)
        slashd (float): minimum distance for slashes to be effective
        sfx_slash (pygame.mixer.Sound): sound effect of slashed enemy
        sfx_lose (pygame.mixer.Sound): sound effect to be played when you lose
        export (list of defaultdict): records of game states
        export_dir (str): directory containing records of game states
        export_rate (float): milliseconds per snapshot
        next_export (float): time until next snapshot (in ms)
    """
    def __init__(self, fps, size, headless, export_dir, export_rate):
        self.fps = fps
        self.w, self.h = size
        if headless:
            self.surface = None
        else:
            self.surface = pygame.display.set_mode(size, pygame.RESIZABLE)
        self.export_dir = path.abspath(export_dir) if export_dir else ''
        self.next_export = self.export_rate = export_rate
        self.export = []

        self.distance = (self.w * self.h / 416) ** 0.5
        self.x, self.y = self.w // 2, self.h // 2
        self.centerx, self.centery = self.w / 2.0, self.h / 2.0
        w, h = (int(i/self.distance/2 + 1) for i in size)
        self.rangex = list(range(MIDDLE - w, MIDDLE + w + 1))
        self.rangey = list(range(MIDDLE - h, MIDDLE + h + 1))
        self.score = INIT_SCORE

        self.map = deque(deque(EMPTY for _ in range(MAZE_SIZE * CELL_WIDTH))
                         for _ in range(MAZE_SIZE * CELL_WIDTH))
        for x in range(MAZE_SIZE):
            for y in range(MAZE_SIZE): self.new_cell(x, y)
        self.vx = self.vy = 0.0
        self.rotatex = self.rotatey = 0
        self.bullets, self.enemies = [], []
        self.enemy_weights = {color: MINW for color in ENEMIES}
        self.add_enemy()
        self.hero = Hero(self.surface, fps, size)
        self.map[MIDDLE][MIDDLE] = HERO
        self.destx = self.desty = MIDDLE
        self.stepx = self.stepy = 0
        self.target = LockOn(MIDDLE, MIDDLE, retired=True)
        self.next_move = self.glitch = self.next_slashfx = 0.0
        self.slashd = self.hero.R + self.distance/SQRT2

        self.sfx_spawn = SFX_SPAWN
        self.sfx_slash = SFX_SLASH_ENEMY
        self.sfx_lose = SFX_LOSE

    def new_cell(self, x, y):
        """Draw on the map a new cell whose coordinates are given.

        For the sake of performance, cell corners are NOT redrawn.
        """
        def draw_bit(bit, dx=0, dy=0):
            startx, starty = x + CELL_NODES[dx], y + CELL_NODES[dy]
            height = ROAD_WIDTH if dy else WALL_WIDTH
            for i in range(ROAD_WIDTH if dx else WALL_WIDTH):
                for j in range(height): self.map[startx + i][starty + j] = bit

        x, y = x * CELL_WIDTH, y * CELL_WIDTH
        draw_bit(WALL)
        walls = set(sample(ADJACENTS, 2))
        walls.add(choice(ADJACENTS))
        for i, j in ADJACENTS:
            draw_bit((WALL if (i, j) in walls else EMPTY), i, j)

    def add_enemy(self):
        """Add enough enemies."""
        walls = [(i, j) for i in self.rangex for j in self.rangey
                 if self.map[i][j] == WALL]
        plums = [e for e in self.enemies if e.color == 'Plum' and e.awake]
        plum = choice(plums) if plums else None
        num = log(self.score, INIT_SCORE)
        while walls and len(self.enemies) < num:
            x, y = choice(walls)
            if all(self.map[x + a][y + b] == WALL for a, b in ADJACENTS):
                continue
            enemy = new_enemy(self, x, y)
            self.enemies.append(enemy)
            if plum is None or not plum.clone(enemy): walls.remove((x, y))

    def get_pos(self, x, y):
        """Return coordinate of the center of the grid (x, y)."""
        return (self.centerx + (x - MIDDLE)*self.distance,
                self.centery + (y - MIDDLE)*self.distance)

    def get_grid(self, x, y):
        """Return the grid containing the point (x, y)."""
        return (MIDDLE + round2((x-self.centerx) / self.distance),
                MIDDLE + round2((y-self.centery) / self.distance))

    def get_target(self, x, y):
        """Return shooting target the grid containing the point (x, y).

        If the grid is the hero, return a retired target.
        """
        gridx, gridy = self.get_grid(x, y)
        if gridx == gridy == MIDDLE: return LockOn(gridx, gridy, True)
        for enemy in self.enemies:
            if not enemy.isunnoticeable(gridx, gridy): return enemy
        return LockOn(gridx, gridy)

    def get_score(self):
        """Return the current score."""
        return int(self.score - INIT_SCORE)

    def get_color(self):
        """Return color of a grid."""
        return choice(TANGO_VALUES)[0] if self.glitch > 0 else FG_COLOR

    def draw(self):
        """Draw the maze."""
        self.surface.fill(BG_COLOR)
        if self.next_move <= 0:
            for i in self.rangex:
                for j in self.rangey:
                    if self.map[i][j] != WALL: continue
                    x, y = self.get_pos(i, j)
                    square = regpoly(4, self.distance / SQRT2, pi / 4, x, y)
                    fill_aapolygon(self.surface, square, self.get_color())

        for enemy in self.enemies: enemy.draw()
        if not self.hero.dead: self.hero.draw()
        bullet_radius = self.distance / 4
        for bullet in self.bullets: bullet.draw(bullet_radius)
        pygame.display.flip()
        pygame.display.set_caption(
            'Brutal Maze - Score: {}'.format(self.get_score()))

    def isdisplayed(self, x, y):
        """Return True if the grid (x, y) is in the displayable part
        of the map, False otherwise.
        """
        return (self.rangex[0] <= x <= self.rangex[-1]
                and self.rangey[0] <= y <= self.rangey[-1])

    def rotate(self):
        """Rotate the maze if needed."""
        x = int((self.centerx-self.x) * 2 / self.distance)
        y = int((self.centery-self.y) * 2 / self.distance)
        if x == y == 0: return
        for enemy in self.enemies:
            if self.map[enemy.x][enemy.y] == ENEMY:
                self.map[enemy.x][enemy.y] = EMPTY

        self.map[MIDDLE][MIDDLE] = EMPTY
        self.centerx -= x * self.distance
        self.map.rotate(x)
        self.rotatex += x
        self.centery -= y * self.distance
        for d in self.map: d.rotate(y)
        self.rotatey += y
        self.map[MIDDLE][MIDDLE] = HERO
        if self.map[self.destx][self.desty] != HERO:
            self.destx += x
            self.desty += y
        self.stepx = self.stepy = 0

        # Respawn the enemies that fall off the display
        killist = []
        for i, enemy in enumerate(self.enemies):
            enemy.place(x, y)
            if not self.isdisplayed(enemy.x, enemy.y):
                self.score += enemy.wound
                enemy.die()
                killist.append(i)
        for i in reversed(killist): self.enemies.pop(i)
        self.add_enemy()

        # LockOn target is not yet updated.
        if isinstance(self.target, LockOn):
            self.target.place(x, y, self.isdisplayed)

        # Regenerate the maze
        if abs(self.rotatex) == CELL_WIDTH:
            self.rotatex = 0
            for i in range(CELL_WIDTH): self.map[i].rotate(-self.rotatey)
            for i in range(MAZE_SIZE): self.new_cell(0, i)
            for i in range(CELL_WIDTH): self.map[i].rotate(self.rotatey)
        if abs(self.rotatey) == CELL_WIDTH:
            self.rotatey = 0
            self.map.rotate(-self.rotatex)
            for i in range(MAZE_SIZE): self.new_cell(i, 0)
            self.map.rotate(self.rotatex)

    def get_distance(self, x, y):
        """Return the distance from the center of the maze to the point
        (x, y).
        """
        return ((self.x-x)**2 + (self.y-y)**2)**0.5

    def hit_hero(self, wound, color):
        """Handle the hero when he loses HP."""
        if self.enemy_weights[color] + wound < MAXW:
            self.enemy_weights[color] += wound
        if color == 'Orange':
            # If called by close-range attack, this is FPS-dependant, although
            # in playable FPS (24 to infinity), the difference within 2%.
            self.hero.next_heal = abs(self.hero.next_heal * (1 - wound))
        elif (uniform(0, sum(self.enemy_weights.values()))
              < self.enemy_weights[color]):
            self.hero.next_heal = -1.0  # what doesn't kill you heals you
            if color == 'Butter' or color == 'ScarletRed':
                wound *= ENEMY_HP
            elif color == 'Chocolate':
                self.hero.highness += wound
                wound = 0
            elif color == 'SkyBlue':
                self.next_move = max(self.next_move, 0) + wound*1000
                wound = 0
        if wound and sum(self.hero.wounds) < MAX_WOUND:
            self.hero.wounds[-1] += wound

    def slash(self):
        """Handle close-range attacks."""
        for enemy in self.enemies: enemy.slash()
        if not self.hero.spin_queue: return
        killist = []
        for i, enemy in enumerate(self.enemies):
            d = self.slashd - enemy.distance
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
        self.bullets.extend(self.hero.shots)
        fallen = []
        block = (self.hero.spin_queue and self.hero.next_heal < 0
                 and self.hero.next_strike > self.hero.spin_queue / self.fps)

        for i, bullet in enumerate(self.bullets):
            wound = bullet.fall_time / BULLET_LIFETIME
            bullet.update(self.fps, self.distance)
            gridx, gridy = self.get_grid(bullet.x, bullet.y)
            if wound <= 0 or not self.isdisplayed(gridx, gridy):
                fallen.append(i)
            elif bullet.color == 'Aluminium':
                if self.map[gridx][gridy] == WALL and self.next_move <= 0:
                    self.glitch = wound * 1000
                    enemy = new_enemy(self, gridx, gridy)
                    enemy.awake = True
                    self.map[gridx][gridy] = ENEMY
                    play(self.sfx_spawn, enemy.spawn_volumn, enemy.get_angle())
                    enemy.hit(wound)
                    self.enemies.append(enemy)
                    fallen.append(i)
                    continue
                for j, enemy in enumerate(self.enemies):
                    if not enemy.awake: continue
                    if bullet.get_distance(*enemy.pos) < self.distance:
                        enemy.hit(wound)
                        if enemy.wound >= ENEMY_HP:
                            self.score += enemy.wound
                            enemy.die()
                            self.enemies.pop(j)
                        play(bullet.sfx_hit, wound, bullet.angle)
                        fallen.append(i)
                        break
            elif bullet.get_distance(self.x, self.y) < self.distance:
                if block:
                    self.hero.next_strike = (abs(self.hero.spin_queue/self.fps)
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
            if max(abs(herox - x), abs(heroy - y)) * 2 < self.distance:
                return 0.0
        return vx or vy

    def expos(self, x, y):
        """Return position of the given coordinates in rounded percent."""
        cx = len(self.rangex)*50 + (x - self.centerx)/self.distance*100
        cy = len(self.rangey)*50 + (y - self.centery)/self.distance*100
        return round2(cx), round2(cy)

    def update_export(self, forced=False):
        """Update the maze's data export and return the last record."""
        if self.next_export > 0 and not forced or self.hero.dead: return
        export = defaultdict(list)
        export['s'] = self.get_score()

        if self.next_move <= 0:
            for y in self.rangey:
                export['m'].append(''.join(
                    COLORS[self.get_color()] if self.map[x][y] == WALL else '0'
                    for x in self.rangex))

        x, y = self.expos(self.x, self.y)
        export['h'] = [
            COLORS[self.hero.get_color()], x, y, deg(self.hero.angle),
            int(self.hero.next_strike <= 0), int(self.hero.next_heal <= 0)]

        for enemy in self.enemies:
            if enemy.isunnoticeable(): continue
            x, y = self.expos(*enemy.pos)
            color, angle = COLORS[enemy.get_color()], deg(enemy.angle)
            export['e'].append([color, x, y, angle])

        for bullet in self.bullets:
            x, y = self.expos(bullet.x, bullet.y)
            color, angle = COLORS[bullet.get_color()], deg(bullet.angle)
            if color != '0': export['b'].append([color, x, y, angle])

        if self.next_export <= 0:
            export['t'] = round2(self.export_rate - self.next_export)
            self.export.append(export)
            self.next_export = self.export_rate
        return export

    def update(self, fps):
        """Update the maze."""
        self.fps = fps
        self.vx = self.is_valid_move(vx=self.vx)
        self.centerx += self.vx
        self.vy = self.is_valid_move(vy=self.vy)
        self.centery += self.vy

        self.next_move -= 1000.0 / fps
        self.glitch -= 1000.0 / fps
        self.next_slashfx -= 1000.0 / fps
        self.next_export -= 1000.0 / fps

        self.rotate()
        if self.vx or self.vy or self.hero.firing or self.hero.slashing:
            for enemy in self.enemies: enemy.wake()
            for bullet in self.bullets: bullet.place(self.vx, self.vy)

        for enemy in self.enemies: enemy.update()
        self.track_bullets()
        if not self.hero.dead:
            self.hero.update(fps)
            self.slash()
            if self.hero.wound >= HERO_HP: self.lose()
        self.update_export()

    def resize(self, size):
        """Resize the maze."""
        self.w, self.h = size
        self.surface = pygame.display.set_mode(size, pygame.RESIZABLE)
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

    def set_step(self, check=(lambda x, y: True)):
        """Work out next step on the shortest path to the destination.

        Return whether target is impossible to reach and hero should
        shoot toward it instead.
        """
        if self.stepx or self.stepy and self.vx == self.vy == 0.0:
            x, y = MIDDLE - self.stepx, MIDDLE - self.stepy
            if self.stepx and not self.stepy:
                nextx = x - self.stepx
                n = self.map[x][y - 1] == EMPTY == self.map[nextx][y - 1]
                s = self.map[x][y + 1] == EMPTY == self.map[nextx][y + 1]
                self.stepy = n - s
            elif not self.stepx and self.stepy:
                nexty = y - self.stepy
                w = self.map[x - 1][y] == EMPTY == self.map[x - 1][nexty]
                e = self.map[x + 1][y] == EMPTY == self.map[x + 1][nexty]
                self.stepx = w - e
            return False

        # Shoot WALL and ENEMY instead
        if self.map[self.destx][self.desty] != EMPTY:
            self.stepx = self.stepy = 0
            return True

        # Forest Fire algorithm with step count
        queue = defaultdict(list, {0: [(self.destx, self.desty)]})
        visited, count, distance = set(), 1, 0
        while count:
            if not queue[distance]: distance += 1
            x, y = queue[distance].pop()
            count -= 1
            if (x, y) not in visited:
                visited.add((x, y))
            else:
                continue

            dx, dy = MIDDLE - x, MIDDLE - y
            if dx**2 + dy**2 <= 2:
                self.stepx, self.stepy = dx, dy
                return False
            for i, j in around(x, y):
                if self.map[i][j] == EMPTY and check(i, j):
                    queue[distance + 1].append((i, j))
                    count += 1

        # Failed to find way to move to target
        self.stepx = self.stepy = 0
        return True

    def isfast(self):
        """Return if the hero is moving faster than HERO_SPEED."""
        return (self.vx**2+self.vy**2)**0.5*self.fps > HERO_SPEED*self.distance

    def dump_records(self):
        """Dump JSON records."""
        if self.export_dir:
            with open(json_rec(self.export_dir), 'w') as f:
                json.dump(self.export, f, separators=JSON_SEPARATORS)

    def lose(self):
        """Handle loses."""
        self.hero.dead = True
        self.hero.wound = HERO_HP
        self.hero.slashing = self.hero.firing = False
        self.destx = self.desty = MIDDLE
        self.stepx = self.stepy = 0
        self.vx = self.vy = 0.0
        play(self.sfx_lose)
        self.dump_records()

    def reinit(self):
        """Open new game."""
        self.centerx, self.centery = self.w / 2.0, self.h / 2.0
        self.score, self.export = INIT_SCORE, []
        self.map = deque(deque(EMPTY for _ in range(MAZE_SIZE * CELL_WIDTH))
                         for _ in range(MAZE_SIZE * CELL_WIDTH))
        for x in range(MAZE_SIZE):
            for y in range(MAZE_SIZE): self.new_cell(x, y)
        self.map[MIDDLE][MIDDLE] = HERO
        self.destx = self.desty = MIDDLE
        self.stepx = self.stepy = 0
        self.vx = self.vy = 0.0
        self.rotatex = self.rotatey = 0
        self.bullets, self.enemies = [], []
        self.enemy_weights = {color: MINW for color in ENEMIES}
        self.add_enemy()

        self.next_move = self.next_slashfx = self.hero.next_strike = 0.0
        self.target = LockOn(MIDDLE, MIDDLE, retired=True)
        self.hero.next_heal = -1.0
        self.hero.highness = 0.0
        self.hero.slashing = self.hero.firing = self.hero.dead = False
        self.hero.spin_queue = self.hero.wound = 0.0
        self.hero.wounds = deque([0.0])
