# -*- coding: utf-8 -*-
# game.py - main module, starts game and main loop
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

__version__ = '0.7.3'

import re
from argparse import ArgumentParser, FileType, RawTextHelpFormatter
from collections import deque
try:                    # Python 3
    from configparser import ConfigParser
except ImportError:     # Python 2
    from ConfigParser import ConfigParser
from math import atan2, radians, pi
from os.path import join, pathsep
from socket import socket, SOL_SOCKET, SO_REUSEADDR
from sys import stdout
from threading import Thread

import pygame
from pygame import KEYDOWN, QUIT, VIDEORESIZE
from pygame.time import Clock, get_ticks
from appdirs import AppDirs

from .constants import (
    SETTINGS, ICON, MUSIC, NOISE, HERO_SPEED, COLORS, MIDDLE, WALL)
from .maze import Maze
from .misc import deg, round2, sign


class ConfigReader:
    """Object reading and processing INI configuration file for
    Brutal Maze.
    """
    CONTROL_ALIASES = (('New game', 'new'), ('Toggle pause', 'pause'),
                       ('Toggle mute', 'mute'),
                       ('Move left', 'left'), ('Move right', 'right'),
                       ('Move up', 'up'), ('Move down', 'down'),
                       ('Auto move', 'autove'),
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
        self.size = (self.config.getint('Graphics', 'Screen width'),
                     self.config.getint('Graphics', 'Screen height'))
        self.max_fps = self.config.getint('Graphics', 'Maximum FPS')
        self.muted = self.config.getboolean('Sound', 'Muted')
        self.musicvol = self.config.getfloat('Sound', 'Music volume')
        self.space = self.config.getboolean('Sound', 'Space theme')
        self.server = self.config.getboolean('Server', 'Enable')
        self.host = self.config.get('Server', 'Host')
        self.port = self.config.getint('Server', 'Port')
        self.timeout = self.config.getfloat('Server', 'Timeout')
        self.headless = self.config.getboolean('Server', 'Headless')

        if self.server: return
        self.key, self.mouse = {}, {}
        for cmd, alias in self.CONTROL_ALIASES:
            i = self.config.get('Control', cmd)
            if re.match('mouse[1-3]$', i.lower()):
                if alias not in ('autove', 'shot', 'slash'):
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
        for option in ('size', 'max_fps', 'muted', 'musicvol', 'space',
                       'server', 'host', 'port', 'timeout', 'headless'):
            value = getattr(arguments, option)
            if value is not None: setattr(self, option, value)


class Game:
    """Object handling main loop and IO."""
    def __init__(self, config):
        pygame.mixer.pre_init(frequency=44100)
        pygame.init()
        self.headless = config.headless and config.server
        if config.muted or self.headless:
            pygame.mixer.quit()
        else:
            pygame.mixer.music.load(NOISE if config.space else MUSIC)
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
            self.timeout = config.timeout
            self.sockinp = 0, 0, -pi * 3 / 4, 0, 0  # freeze and point to NW
        else:
            self.server = self.sockinp = None

        # self.fps is a float to make sure floordiv won't be used in Python 2
        self.max_fps, self.fps = config.max_fps, float(config.max_fps)
        self.musicvol = config.musicvol
        self.key, self.mouse = config.key, config.mouse
        self.maze = Maze(config.max_fps, config.size, config.headless)
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
        maze, hero, = self.maze, self.hero
        lines = deque(['{0} {4} {5} {1} {2:d} {3:d}'.format(
            COLORS[hero.get_color()], deg(self.hero.angle),
            hero.next_strike <= 0, hero.next_heal <= 0,
            *self.expos(maze.x, maze.y))])

        walls = [[1 if maze.map[x][y] == WALL else 0 for x in maze.rangex]
                 for y in maze.rangey] if maze.next_move <= 0 else []
        ne = nb = 0

        for enemy in maze.enemies:
            # Check Chameleons
            if getattr(enemy, 'visible', 1) <= 0 and maze.next_move <= 0:
                continue
            lines.append('{0} {2} {3} {1:.0f}'.format(
                COLORS[enemy.get_color()], deg(enemy.angle),
                *self.expos(*enemy.get_pos())))
            ne += 1

        for bullet in maze.bullets:
            x, y = self.expos(bullet.x, bullet.y)
            color, angle = COLORS[bullet.get_color()], deg(bullet.angle)
            if color != '0':
                lines.append('{} {} {} {:.0f}'.format(color, x, y, angle))
                nb += 1

        if walls: lines.appendleft('\n'.join(''.join(str(cell) for cell in row)
                                             for row in walls))
        lines.appendleft('{} {} {} {}'.format(len(walls), ne, nb,
                                              maze.get_score()))
        return '\n'.join(lines).encode()

    def update(self):
        """Draw and handle meta events on Pygame window.

        Return False if QUIT event is captured, True otherwise.
        """
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

        # Compare current FPS with the average of the last 10 frames
        new_fps = self.clock.get_fps()
        if new_fps < self.fps:
            self.fps -= 1
        elif self.fps < self.max_fps and not self.paused:
            self.fps += 5
        if not self.paused: self.maze.update(self.fps)
        if not self.headless: self.maze.draw()
        self.clock.tick(self.fps)
        return True

    def move(self, x, y):
        """Command the hero to move faster in the given direction."""
        maze = self.maze
        velocity = maze.distance * HERO_SPEED / self.fps
        accel = velocity * HERO_SPEED / self.fps

        if x == y == 0:
            maze.set_step()
            x, y = maze.stepx, maze.stepy
        else:
            x, y = -x, -y   # or move the maze in the reverse direction

        if maze.next_move > 0 or not x:
            maze.vx -= sign(maze.vx) * accel
            if abs(maze.vx) < accel * 2: maze.vx = 0.0
        elif x * maze.vx < 0:
            maze.vx += x * 2 * accel
        else:
            maze.vx += x * accel
            if abs(maze.vx) > velocity: maze.vx = x * velocity

        if maze.next_move > 0 or not y:
            maze.vy -= sign(maze.vy) * accel
            if abs(maze.vy) < accel * 2: maze.vy = 0.0
        elif y * maze.vy < 0:
            maze.vy += y * 2 * accel
        else:
            maze.vy += y * accel
            if abs(maze.vy) > velocity: maze.vy = y * velocity

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
        clock = Clock()
        while True:
            connection, address = self.server.accept()
            connection.settimeout(self.timeout)
            time = get_ticks()
            print('[{}] Connected to {}:{}'.format(time, *address))
            self.maze.reinit()
            while True:
                if self.hero.dead:
                    connection.send('0000000'.encode())
                    break
                data = self.export()
                connection.send('{:07}'.format(len(data)).encode())
                connection.send(data)
                try:
                    buf = connection.recv(7)
                except:     # client is closed or timed out
                    break
                if not buf: break
                try:
                    move, angle, attack = map(int, buf.decode().split())
                except ValueError:  # invalid input
                    break
                y, x = (i - 1 for i in divmod(move, 3))
                self.sockinp = x, y, radians(angle), attack & 1, attack >> 1
                clock.tick(self.fps)
            self.sockinp = 0, 0, -pi * 3 / 4, 0, 0
            new_time = get_ticks()
            print('[{0}] {3}:{4} scored {1} points in {2}ms'.format(
                new_time, self.maze.get_score(), new_time - time, *address))
            connection.close()
            if not self.hero.dead: self.maze.lose()

    def user_control(self):
        """Handle direct control from user's mouse and keyboard."""
        if not self.hero.dead:
            keys = pygame.key.get_pressed()
            right = keys[self.key['right']] - keys[self.key['left']]
            down = keys[self.key['down']] - keys[self.key['up']]

            buttons = pygame.mouse.get_pressed()
            try:
                autove = keys[self.key['autove']]
            except KeyError:
                autove = buttons[self.mouse['autove']]
            try:
                firing = keys[self.key['shot']]
            except KeyError:
                firing = buttons[self.mouse['shot']]
            try:
                slashing = keys[self.key['slash']]
            except KeyError:
                slashing = buttons[self.mouse['slash']]

            # Follow the mouse cursor
            x, y = pygame.mouse.get_pos()
            maze = self.maze
            if right or down:
                maze.destx = maze.desty = MIDDLE
                maze.stepx = maze.stepy = 0
            elif autove:
                maze.destx, maze.desty = maze.get_grid(x, y)
                maze.set_step(lambda x: maze.rangex[0] <= x <= maze.rangex[-1],
                              lambda y: maze.rangey[0] <= y <= maze.rangey[-1])
                if maze.stepx == maze.stepy == 0:
                    maze.destx = maze.desty = MIDDLE

            angle = atan2(y - self.hero.y, x - self.hero.x)
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
    parser = ArgumentParser(usage='%(prog)s [options]',
                            formatter_class=RawTextHelpFormatter)
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
        '-f', '--max-fps', type=int, metavar='FPS',
        help='the desired maximum FPS (fallback: {})'.format(config.max_fps))
    parser.add_argument(
        '--mute', '-m', action='store_true', default=None, dest='muted',
        help='mute all sounds (fallback: {})'.format(config.muted))
    parser.add_argument('--unmute', action='store_false', dest='muted',
                        help='unmute sound')
    parser.add_argument(
        '--music-volume', type=float, metavar='VOL', dest='musicvol',
        help='between 0.0 and 1.0 (fallback: {})'.format(config.musicvol))
    parser.add_argument(
        '--space-music', action='store_true', default=None, dest='space',
        help='use space music background'.format(config.muted))
    parser.add_argument('--default-music', action='store_false', dest='space',
                        help='use default music background')
    parser.add_argument(
        '--server', action='store_true', default=None,
        help='enable server (fallback: {})'.format(config.server))
    parser.add_argument('--no-server', action='store_false', dest='server',
                        help='disable server')
    parser.add_argument(
        '--host', help='host to bind server to (fallback: {})'.format(
            config.host))
    parser.add_argument(
        '--port', type=int,
        help='port for server to listen on (fallback: {})'.format(config.port))
    parser.add_argument(
        '-t', '--timeout', type=float,
        help='socket operations timeout in seconds (fallback: {})'.format(
            config.timeout))
    parser.add_argument(
        '--head', action='store_false', default=None, dest='headless',
        help='run server with graphics and sound (fallback: {})'.format(
            not config.headless))
    parser.add_argument('--headless', action='store_true',
                        help='run server without graphics or sound')
    args = parser.parse_args()
    if args.defaultcfg is not None:
        with open(SETTINGS) as settings: args.defaultcfg.write(settings.read())
        args.defaultcfg.close()
        exit()

    # Manipulate config
    if args.config:
        config.config.read(args.config)
        config.parse()
    config.read_args(args)

    # Main loop
    with Game(config) as game:
        if config.server:
            socket_thread = Thread(target=game.remote_control)
            socket_thread.daemon = True     # make it disposable
            socket_thread.start()
            while game.update(): game.control(*game.sockinp)
        else:
            while game.update(): game.user_control()
