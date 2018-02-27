# -*- coding: utf-8 -*-
# main.py - main module, starts game and main loop
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

__version__ = '0.5.4'

import re
from argparse import ArgumentParser, FileType, RawTextHelpFormatter
from collections import deque
try:                    # Python 3
    from configparser import ConfigParser
except ImportError:     # Python 2
    from ConfigParser import ConfigParser
from itertools import repeat
from math import atan2, degrees, radians
from os.path import join, pathsep
from socket import socket, SOL_SOCKET, SO_REUSEADDR
from sys import stdout
from threading import Thread


import pygame
from pygame import DOUBLEBUF, KEYDOWN, OPENGL, QUIT, RESIZABLE, VIDEORESIZE
from pygame.time import Clock, get_ticks
from appdirs import AppDirs

from .constants import SETTINGS, ICON, MUSIC, HERO_SPEED, COLORS, WALL
from .maze import Maze
from .misc import round2, sign


class ConfigReader:
    """Object reading and processing INI configuration file for
    Brutal Maze.
    """
    CONTROL_ALIASES = (('New game', 'new'), ('Toggle pause', 'pause'),
                       ('Toggle mute', 'mute'),
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

    # Fallback to None when attribute is missing
    def __getattr__(self, name): return None

    def parse(self):
        """Parse configurations."""
        self.server = self.config.getboolean('Server', 'Enable')
        if self.server:
            self.host = self.config.get('Server', 'Host')
            self.port = self.config.getint('Server', 'Port')
            self.headless = self.config.getboolean('Server', 'Headless')
        else:
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

        self.size = (self.config.getint('Graphics', 'Screen width'),
                     self.config.getint('Graphics', 'Screen height'))
        self.opengl = self.config.getboolean('Graphics', 'OpenGL')
        self.max_fps = self.config.getint('Graphics', 'Maximum FPS')
        self.muted = self.config.getboolean('Sound', 'Muted')
        self.musicvol = self.config.getfloat('Sound', 'Music volume')

    def read_args(self, arguments):
        """Read and parse a ArgumentParser.Namespace."""
        for option in 'size', 'opengl', 'max_fps', 'muted', 'musicvol':
            value = getattr(arguments, option)
            if value is not None: setattr(self, option, value)


class Game:
    """Object handling main loop and IO."""
    def __init__(self, config):
        pygame.mixer.pre_init(frequency=44100)
        pygame.init()
        if config.muted or config.headless:
            pygame.mixer.quit()
        else:
            pygame.mixer.music.load(MUSIC)
            pygame.mixer.music.set_volume(config.musicvol)
            pygame.mixer.music.play(-1)
        pygame.display.set_icon(ICON)

        pygame.fastevent.init()
        if config.server:
            self.server = socket()
            self.server.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
            self.server.bind((config.host, config.port))
            self.server.listen(1)
            print('Socket server is listening on {}:{}'.format(config.host,
                                                               config.port))
        else:
            self.server = None

        self.headless = config.headless
        # self.fps is a float to make sure floordiv won't be used in Python 2
        self.max_fps, self.fps = config.max_fps, float(config.max_fps)
        self.musicvol = config.musicvol
        self.key, self.mouse = config.key, config.mouse
        scrtype = (config.opengl and DOUBLEBUF|OPENGL) | RESIZABLE
        self.maze = Maze(config.max_fps, config.size, scrtype, config.headless)
        self.hero = self.maze.hero
        self.clock, self.paused = Clock(), False

    def __enter__(self): return self

    def expos(self, x, y):
        """Return position of the given coordinates in rounded percent."""
        cx = (x+self.maze.x-self.maze.centerx) / self.maze.distance * 100
        cy = (y+self.maze.y-self.maze.centery) / self.maze.distance * 100
        return round2(cx), round2(cy)

    def export(self):
        """Export maze data to a bytes object."""
        maze, hero, tick = self.maze, self.hero, get_ticks()
        walls = [[1 if maze.map[x][y] == WALL else 0 for x in maze.rangex]
                 for y in maze.rangey] if maze.next_move <= tick else []
        lines, ne, nb = deque(), 0, 0

        for enemy in maze.enemies:
            if not enemy.awake and walls:
                walls[enemy.y-maze.rangey[0]][enemy.x-maze.rangex[0]] = WALL
                continue
            elif enemy.color == 'Chameleon' and maze.next_move <= tick:
                continue
            x, y = self.expos(*enemy.get_pos())
            lines.append('{} {} {} {:.0f}'.format(COLORS[enemy.get_color()],
                                                  x, y, degrees(enemy.angle)))
            ne += 1

        for bullet in maze.bullets:
            x, y = self.expos(bullet.x, bullet.y)
            color, angle = COLORS[bullet.get_color()], degrees(bullet.angle)
            if color != '0':
                lines.append('{} {} {} {:.0f}'.format(color, x, y, angle))
                nb += 1

        if walls: lines.appendleft('\n'.join(''.join(str(cell) for cell in row)
                                             for row in walls))
        x, y = self.expos(maze.x, maze.y)
        lines.appendleft('{} {} {} {} {} {} {:.0f} {:d} {:d}'.format(
            len(walls), ne, nb, maze.get_score(), x, y, hero.wound * 100,
            hero.next_strike <= tick, hero.next_heal <= tick))
        return '\n'.join(lines).encode()

    def update(self):
        """Draw and handle meta events on Pygame window.

        Return False if QUIT event is captured, True otherwise.
        """
        # Compare current FPS with the average of the last 10 frames
        new_fps = self.clock.get_fps()
        if new_fps < self.fps:
            self.fps -= 1
        elif self.fps < self.max_fps and not self.paused:
            self.fps += 5
        if not self.paused: self.maze.update(self.fps)

        self.clock.tick(self.fps)
        events = pygame.fastevent.get()
        for event in events:
            if event.type == QUIT:
                return False
            elif event.type == VIDEORESIZE:
                self.maze.resize((event.w, event.h))
            elif event.type == KEYDOWN and not self.server:
                if event.key == self.key['new']:
                    self.maze.reinit()
                elif event.key == self.key['pause'] and not self.hero.dead:
                    self.paused ^= True
                elif event.key == self.key['mute']:
                    if pygame.mixer.get_init() is None:
                        pygame.mixer.init(frequency=44100)
                        pygame.mixer.music.load(MUSIC)
                        pygame.mixer.music.set_volume(self.musicvol)
                        pygame.mixer.music.play(-1)
                    else:
                        pygame.mixer.quit()
        if not self.headless: self.maze.draw()
        return True

    def move(self, x, y):
        """Command the hero to move faster in the given direction."""
        x, y = -x, -y # or move the maze in the reverse direction
        stunned = pygame.time.get_ticks() < self.maze.next_move
        velocity = self.maze.distance * HERO_SPEED / self.fps
        accel = velocity * HERO_SPEED / self.fps

        if stunned or not x:
            self.maze.vx -= sign(self.maze.vx) * accel
            if abs(self.maze.vx) < accel * 2: self.maze.vx = 0.0
        elif x * self.maze.vx < 0:
            self.maze.vx += x * 2 * accel
        else:
            self.maze.vx += x * accel
            if abs(self.maze.vx) > velocity: self.maze.vx = x * velocity

        if stunned or not y:
            self.maze.vy -= sign(self.maze.vy) * accel
            if abs(self.maze.vy) < accel * 2: self.maze.vy = 0.0
        elif y * self.maze.vy < 0:
            self.maze.vy += y * 2 * accel
        else:
            self.maze.vy += y * accel
            if abs(self.maze.vy) > velocity: self.maze.vy = y * velocity

    def control(self, x, y, angle, firing, slashing):
        """Control how the hero move and attack."""
        self.move(x, y)
        self.hero.update_angle(angle)
        self.hero.firing = firing
        self.hero.slashing = slashing

    def remote_control(self):
        """Handle remote control though socket server.

        This function is supposed to be run in a Thread.
        """
        while True:
            connection, address = self.server.accept()
            print('Connected to {}:{}'.format(*address))
            self.maze.reinit()
            while not self.hero.dead:
                data = self.export()
                connection.send('{:06}'.format(len(data)).encode())
                connection.send(data)
                buf = connection.recv(8)
                if not buf: break
                move, angle, attack = (int(i) for i in buf.decode().split())
                y, x = (i - 1 for i in divmod(move, 3))
                self.control(x, y, radians(angle), attack & 1, attack >> 1)
            self.maze.lose()
            print('{1}:{2} scored {0} points'.format(
                self.maze.get_score(), *address))
            connection.close()

    def user_control(self):
        """Handle direct control from user's mouse and keyboard."""
        if not self.hero.dead:
            keys = pygame.key.get_pressed()
            right = keys[self.key['right']] - keys[self.key['left']]
            down = keys[self.key['down']] - keys[self.key['up']]

            # Follow the mouse cursor
            x, y = pygame.mouse.get_pos()
            angle = atan2(y - self.hero.y, x - self.hero.x)

            buttons = pygame.mouse.get_pressed()
            try:
                firing = keys[self.key['shot']]
            except KeyError:
                firing = buttons[self.mouse['shot']]
            try:
                slashing = keys[self.key['slash']]
            except KeyError:
                slashing = buttons[self.mouse['slash']]

            self.control(right, down, angle, firing, slashing)

    def __exit__(self, exc_type, exc_value, traceback):
        if self.server is not None: self.server.close()
        pygame.quit()


def main():
    """Start game and main loop."""
    # Read configuration file
    dirs = AppDirs(appname='brutalmaze', appauthor=False, multipath=True)
    parents = dirs.site_config_dir.split(pathsep)
    parents.append(dirs.user_config_dir)
    filenames = [join(parent, 'settings.ini') for parent in parents]
    config = ConfigReader(filenames)
    config.parse()

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
        '-f', '--max-fps', type=int, metavar='FPS',
        help='the desired maximum FPS (fallback: {})'.format(config.max_fps))
    parser.add_argument(
        '--mute', '-m', action='store_true', default=None,
        help='mute all sounds (fallback: {})'.format(config.muted))
    parser.add_argument('--unmute', action='store_false', dest='muted',
                        help='unmute sound')
    parser.add_argument(
        '--music-volume', type=float, metavar='VOL', dest='musicvol',
        help='between 0.0 and 1.0 (fallback: {})'.format(config.musicvol))
    args = parser.parse_args()
    if args.defaultcfg is not None:
        with open(SETTINGS) as settings: args.defaultcfg.write(settings.read())
        args.defaultcfg.close()
        exit()

    # Manipulate config
    if args.config: config.config.read(args.config)
    config.read_args(args)
    config.parse()

    # Main loop
    with Game(config) as game:
        if config.server:
            socket_thread = Thread(target=game.remote_control)
            socket_thread.daemon = True     # make it disposable
            socket_thread.start()
            while game.update(): pass
        else:
            while game.update(): game.user_control()
