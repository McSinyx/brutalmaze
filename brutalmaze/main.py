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

import re
from collections import deque
try:                    # Python 3
    from configparser import ConfigParser, NoOptionError, NoSectionError
except ImportError:     # Python 2
    from ConfigParser import ConfigParser, NoOptionError, NoSectionError

import pygame
from pygame import DOUBLEBUF, KEYDOWN, OPENGL, QUIT, RESIZABLE, VIDEORESIZE

from .constants import USER_CONFIG, SITE_CONFIG, DEFAULT_BINDINGS, ICON, MUSIC
from .maze import Maze


def getconf(config, section, option, valtype=str, fallback=None):
    """Return an option value for a given section from a ConfigParser
    object.

    If the key is not found, return the fallback value.
    """
    if fallback is None: fallback = valtype()
    try:
        if valtype == str:
            return config.get(section, option)
        elif valtype == bool:
            return config.getboolean(section, option)
        elif valtype == float:
            return config.getfloat(section, option)
        elif valtype == int:
            return config.getint(section, option)
    except NoSectionError, NoOptionError:
        return fallback


def main():
    """Start game and main loop."""
    # Read configuration file
    config = ConfigParser()
    conf = config.read(USER_CONFIG)
    if not conf: conf = config.read(SITE_CONFIG)
    conf = conf[0] if conf else ''

    # Read graphics configurations
    width = getconf(config, 'Graphics', 'Screen width', int, 640)
    height = getconf(config, 'Graphics', 'Screen height', int, 480)
    scrtype = RESIZABLE
    if getconf(config, 'Graphics', 'OpenGL', bool):
        scrtype |= OPENGL | DOUBLEBUF
    fps = max_fps = getconf(config, 'Graphics', 'Maximum FPS', float, 60.0)

    # Read control configurations
    key, mouse = {}, {}
    for cmd, bind in DEFAULT_BINDINGS.items():
        i = getconf(config, 'Control', cmd, fallback=bind).lower()
        if re.match('mouse[1-3]$', i):
            if cmd not in ('Long-range attack', 'Close-range attack'):
                print('File "{}", section Control'.format(conf))
                print('\tOne does not simply {} using a mouse'.format(cmd))
                quit()
            mouse[cmd] = int(i[-1]) - 1
            continue
        if len(i) == 1:
            key[cmd] = ord(i)
            continue
        try:
            key[cmd] = getattr(pygame, 'K_{}'.format(i.upper()))
        except AttributeError:
            print('File "{}", section Control, option {}'.format(conf, cmd))
            print('\t"{}" is not recognized as a valid input'.format(i))
            quit()

    # Initialization
    pygame.mixer.pre_init(frequency=44100)
    pygame.init()
    pygame.mixer.music.load(MUSIC)
    pygame.mixer.music.play(-1)
    pygame.display.set_icon(ICON)
    pygame.fastevent.init()
    maze = Maze((width, height), scrtype, fps)
    clock, flash_time, going = pygame.time.Clock(), deque(), True

    # Main loop
    while going:
        events = pygame.fastevent.get()
        for event in events:
            if event.type == QUIT:
                going = False
            elif event.type == VIDEORESIZE:
                maze.resize((event.w, event.h), scrtype)
            elif event.type == KEYDOWN:
                if event.key == key['New game']:
                    maze.__init__((maze.w, maze.h), scrtype, fps)
                elif event.key == key['Pause'] and not maze.hero.dead:
                    maze.paused ^= True

        if not maze.hero.dead:
            keys = pygame.key.get_pressed()
            maze.move(keys[key['Move left']] - keys[key['Move right']],
                      keys[key['Move up']] - keys[key['Move down']], fps)
            buttons = pygame.mouse.get_pressed()
            try:
                maze.hero.firing = keys[key['Long-range attack']]
            except KeyError:
                maze.hero.firing = buttons[mouse['Long-range attack']]
            try:
                maze.hero.slashing = keys[key['Close-range attack']]
            except KeyError:
                maze.hero.slashing = buttons[mouse['Close-range attack']]

        # Compare current FPS with the average of the last 5 seconds
        if len(flash_time) > 5:
            new_fps = 5000.0 / (flash_time[-1] - flash_time[0])
            flash_time.popleft()
            if new_fps < fps:
                fps -= 1
            elif fps < max_fps and not maze.paused:
                fps += 5
        maze.update(fps)
        flash_time.append(pygame.time.get_ticks())
        clock.tick(fps)
    pygame.quit()
