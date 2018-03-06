# -*- coding: utf-8 -*-
# constants.py - module for shared constants
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

__doc__ = 'Brutal Maze module for shared constants'

from string import ascii_lowercase

from pkg_resources import resource_filename as pkg_file
import pygame
from pygame.mixer import Sound

SETTINGS = pkg_file('brutalmaze', 'settings.ini')
ICON = pygame.image.load(pkg_file('brutalmaze', 'icon.png'))
MUSIC = pkg_file('brutalmaze', 'soundfx/music.ogg')

mixer = pygame.mixer.get_init()
if mixer is None: pygame.mixer.init(frequency=44100)
SFX_SPAWN = Sound(pkg_file('brutalmaze', 'soundfx/spawn.ogg'))
SFX_SLASH_ENEMY = Sound(pkg_file('brutalmaze', 'soundfx/slash-enemy.ogg'))
SFX_SLASH_HERO = Sound(pkg_file('brutalmaze', 'soundfx/slash-hero.ogg'))
SFX_SHOT_ENEMY = Sound(pkg_file('brutalmaze', 'soundfx/shot-enemy.ogg'))
SFX_SHOT_HERO = Sound(pkg_file('brutalmaze', 'soundfx/shot-hero.ogg'))
SFX_MISSED = Sound(pkg_file('brutalmaze', 'soundfx/missed.ogg'))
SFX_HEART = Sound(pkg_file('brutalmaze', 'soundfx/heart.ogg'))
SFX_LOSE = Sound(pkg_file('brutalmaze', 'soundfx/lose.ogg'))
if mixer is None: pygame.mixer.quit()

SQRT2 = 2 ** 0.5
INIT_SCORE = 5**0.5/2 + 0.5     # golden mean
MAZE_SIZE = 10
ROAD_WIDTH = 5  # grids
CELL_WIDTH = ROAD_WIDTH * 2     # grids
MIDDLE = (MAZE_SIZE + MAZE_SIZE%2 - 1)*ROAD_WIDTH + ROAD_WIDTH//2
LAST_ROW = (MAZE_SIZE-1) * ROAD_WIDTH * 2
HEAL_SPEED = 1  # HP/s
HERO_SPEED = 5  # grid/s
ENEMY_SPEED = 6 # grid/s
BULLET_SPEED = 15   # grid/s
ATTACK_SPEED = 333.333  # ms/strike
FIRANGE = 6     # grids
BULLET_LIFETIME = 1000.0 * FIRANGE / (BULLET_SPEED-HERO_SPEED)  # ms
EMPTY, WALL, HERO, ENEMY = range(4)
ADJACENT_GRIDS = (1, 0), (0, 1), (-1, 0), (0, -1)
AROUND_HERO = set((MIDDLE + x, MIDDLE + y) for x, y in
                  ADJACENT_GRIDS + ((1, 1), (-1, 1), (-1, -1), (1, -1)))

TANGO = {'Butter': ((252, 233, 79), (237, 212, 0), (196, 160, 0)),
         'Orange': ((252, 175, 62), (245, 121, 0), (206, 92, 0)),
         'Chocolate': ((233, 185, 110), (193, 125, 17), (143, 89, 2)),
         'Chameleon': ((138, 226, 52), (115, 210, 22), (78, 154, 6)),
         'SkyBlue': ((114, 159, 207), (52, 101, 164), (32, 74, 135)),
         'Plum': ((173, 127, 168), (117, 80, 123), (92, 53, 102)),
         'ScarletRed': ((239, 41, 41), (204, 0, 0), (164, 0, 0)),
         'Aluminium': ((238, 238, 236), (211, 215, 207), (186, 189, 182),
                       (136, 138, 133), (85, 87, 83), (46, 52, 54))}
ENEMIES = ['Butter', 'Orange', 'Chocolate', 'Chameleon',
           'SkyBlue', 'Plum', 'ScarletRed']
COLOR_CODE = ascii_lowercase + '0'
COLORS = {c: COLOR_CODE[i] for i, c in enumerate(
    color for code in ENEMIES + ['Aluminium'] for color in TANGO[code])}
MINW, MAXW = 24, 36
ENEMY_HP = 3
HERO_HP = 5
MIN_BEAT = 526
BG_COLOR = TANGO['Aluminium'][-1]
FG_COLOR = TANGO['Aluminium'][0]
