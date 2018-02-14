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

__version__ = '0.5.2'

import re
from argparse import ArgumentParser, FileType, RawTextHelpFormatter
from collections import deque
try:                    # Python 3
    from configparser import ConfigParser, NoOptionError, NoSectionError
except ImportError:     # Python 2
    from ConfigParser import ConfigParser, NoOptionError, NoSectionError
from os.path import join, pathsep
from sys import stdout


import pygame
from pygame import DOUBLEBUF, KEYDOWN, OPENGL, QUIT, RESIZABLE, VIDEORESIZE
from appdirs import AppDirs

from .constants import *
from .maze import Maze


class ConfigReader:
    """Object reading and processing INI configuration file for
    Brutal Maze.
    """
    DEFAULT_BINDINGS = (('New game', 'new'), ('Pause', 'pause'),
                        ('Move left', 'left'), ('Move right', 'right'),
                        ('Move up', 'up'), ('Move down', 'down'),
                        ('Long-range attack', 'shot'),
                        ('Close-range attack', 'slash'))
    WEIRD_MOUSE_ERR = '{}: Mouse is not a suitable control'
    INVALID_CONTROL_ERR = '{}: {} is not recognized as a valid control key'

    def __init__(self, filenames):
        self.config = ConfigParser()
        self.config.read(SETTINGS)  # default configuration
        self.config.read(filenames)

    def parse_graphics(self):
        """Parse graphics configurations."""
        self.size = (self.config.getint('Graphics', 'Screen width'),
                     self.config.getint('Graphics', 'Screen height'))
        self.opengl = self.config.getboolean('Graphics', 'OpenGL')
        self.max_fps = self.config.getfloat('Graphics', 'Maximum FPS')

    def parse_control(self):
        """Parse control configurations."""
        self.key, self.mouse = {}, {}
        for cmd, alias in self.CONTROL_ALIASES:
            i = self.config.get('Control', cmd)
            if re.match('mouse[1-3]$', i.lower()):
                if alias not in ('shot', 'slash'):
                    raise ValueError(self.WEIRD_MOUSE_ERR.format(cmd))
                self.mouse[alias] = int(i[-1]) - 1
                continue
            if len(i) == 1:
                self.key[alias] = ord(i.lower())
                continue
            try:
                self.key[alias] = getattr(pygame, 'K_{}'.format(i.upper()))
            except AttributeError:
                raise ValueError(self.INVALID_CONTROL_ERR.format(cmd, i))

    def read_args(self, arguments):
        """Read and parse a ArgumentParser.Namespace."""
        if arguments.size is not None: self.size = arguments.size
        if arguments.opengl is not None: self.opengl = arguments.opengl
        if arguments.max_fps is not None: self.max_fps = arguments.max_fps


def main():
    """Start game and main loop."""
    # Read configuration file
    dirs = AppDirs(appname='brutalmaze', appauthor=False, multipath=True)
    parents = dirs.site_config_dir.split(pathsep)
    parents.append(dirs.user_config_dir)
    filenames = [join(parent, 'settings.ini') for parent in parents]
    config = ConfigReader(filenames)
    config.parse_graphics()

    # Parse command-line arguments
    parser = ArgumentParser(formatter_class=RawTextHelpFormatter)
    parser.add_argument('-v', '--version', action='version',
                        version='Brutal Maze {}'.format(__version__))
    parser.add_argument(
        '--write-config', nargs='?', const=stdout, type=FileType('w'),
        metavar='PATH', dest='defaultcfg',
        help='write default config and exit, if PATH not specified use stdout')
    parser.add_argument(
        '-c', '--config', metavar='PATH',
        help='location of the configuration file (fallback: {})'.format(
            pathsep.join(filenames)))
    parser.add_argument(
        '-s', '--size', type=int, nargs=2, metavar=('X', 'Y'),
        help='the desired screen size (fallback: {}x{})'.format(*config.size))
    parser.add_argument(
        '--opengl', action='store_true', default=None,
        help='enable OpenGL (fallback: {})'.format(config.opengl))
    parser.add_argument('--no-opengl', action='store_false', dest='opengl',
                        help='disable OpenGL')
    parser.add_argument(
        '-f', '--max-fps', type=float, metavar='FPS',
        help='the desired maximum FPS (fallback: {})'.format(config.max_fps))
    args = parser.parse_args()
    if args.defaultcfg is not None:
        with open(SETTINGS) as settings: args.defaultcfg.write(settings.read())
        args.defaultcfg.close()
        exit()

    # Manipulate config
    if args.config: config.config.read(args.config)
    config.read_args(args)
    config.parse_graphics()
    config.parse_control()

    # Initialization
    pygame.mixer.pre_init(frequency=44100)
    pygame.init()
    pygame.mixer.music.load(MUSIC)
    pygame.mixer.music.play(-1)
    pygame.display.set_icon(ICON)
    pygame.fastevent.init()
    clock, flash_time, fps = pygame.time.Clock(), deque(), config.max_fps
    scrtype = (config.opengl and DOUBLEBUF|OPENGL) | RESIZABLE
    maze = Maze(config.size, scrtype, fps)

    # Main loop
    going = True
    while going:
        events = pygame.fastevent.get()
        for event in events:
            if event.type == QUIT:
                going = False
            elif event.type == VIDEORESIZE:
                maze.resize((event.w, event.h), scrtype)
            elif event.type == KEYDOWN:
                if event.key == config.key['new']:
                    maze.__init__((maze.w, maze.h), scrtype, fps)
                elif event.key == config.key['pause'] and not maze.hero.dead:
                    maze.paused ^= True

        if not maze.hero.dead:
            keys = pygame.key.get_pressed()
            maze.move(keys[config.key['left']] - keys[config.key['right']],
                      keys[config.key['up']] - keys[config.key['down']], fps)
            buttons = pygame.mouse.get_pressed()
            try:
                maze.hero.firing = keys[config.key['shot']]
            except KeyError:
                maze.hero.firing = buttons[config.mouse['shot']]
            try:
                maze.hero.slashing = keys[config.key['slash']]
            except KeyError:
                maze.hero.slashing = buttons[config.mouse['slash']]

        # Compare current FPS with the average of the last 5 seconds
        if len(flash_time) > 5:
            new_fps = 5000.0 / (flash_time[-1] - flash_time[0])
            flash_time.popleft()
            if new_fps < fps:
                fps -= 1
            elif fps < config.max_fps and not maze.paused:
                fps += 5
        maze.update(fps)
        flash_time.append(pygame.time.get_ticks())
        clock.tick(fps)
    pygame.quit()
