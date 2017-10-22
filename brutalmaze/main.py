# -*- coding: utf-8 -*-
# main.py - main module, starts game and main loop
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

import pygame
from pygame.locals import *

from .constants import ICON, SIZE, INIT_FPS, MAX_FPS
from .maze import Maze


def main():
    """Start game and main loop."""
    pygame.init()
    pygame.display.set_icon(ICON)
    pygame.fastevent.init()
    maze, clock = Maze(SIZE, INIT_FPS), pygame.time.Clock()
    fps, flash_time, going = INIT_FPS, deque(), True
    while going:
        events = pygame.fastevent.get()
        for event in events:
            if event.type == QUIT:
                going = False
            elif event.type == KEYDOWN:
                if event.key in (K_ESCAPE, K_p):
                    maze.paused ^= True
                elif event.key in (K_UP, K_w):
                    maze.move(up=-1)
                elif event.key in (K_LEFT, K_a):
                    maze.move(left=-1)
                elif event.key in (K_DOWN, K_s):
                    maze.move(down=-1)
                elif event.key in (K_RIGHT, K_d):
                    maze.move(right=-1)
                elif event.key == K_RETURN:
                    maze.hero.slashing = True
            elif event.type == KEYUP:
                if event.key in (K_UP, K_w):
                    maze.move(up=1)
                elif event.key in (K_LEFT, K_a):
                    maze.move(left=1)
                elif event.key in (K_DOWN, K_s):
                    maze.move(down=1)
                elif event.key in (K_RIGHT, K_d):
                    maze.move(right=1)
                elif event.key == K_RETURN:
                    maze.hero.slashing = False
            elif event.type == MOUSEBUTTONDOWN:
                if event.button == 1:
                    maze.hero.firing = True
                elif event.button == 3:
                    maze.hero.slashing = True
            elif event.type == MOUSEBUTTONUP:
                if event.button == 1:
                    maze.hero.firing = False
                elif event.button == 3:
                    maze.hero.slashing = False
            elif event.type == VIDEORESIZE:
                maze.resize(event.w, event.h)
        if len(flash_time) > 5:
            new_fps = 5000.0 / (flash_time[-1] - flash_time[0])
            flash_time.popleft()
            if new_fps < fps:
                fps -= 1
            elif fps < MAX_FPS and not maze.paused:
                fps += 5
        maze.update(fps)
        flash_time.append(pygame.time.get_ticks())
        clock.tick(fps)
    pygame.quit()
