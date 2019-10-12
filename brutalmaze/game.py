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

__version__ = '0.8.27'

import re
from argparse import ArgumentParser, FileType, RawTextHelpFormatter
try:                    # Python 3
    from configparser import ConfigParser
except ImportError:     # Python 2
    from ConfigParser import ConfigParser
from math import atan2, radians, pi
from os.path import join as pathjoin, pathsep
from socket import socket, SOL_SOCKET, SO_REUSEADDR
from sys import stdout
from threading import Thread

import pygame
from pygame import KEYDOWN, MOUSEBUTTONUP, QUIT, VIDEORESIZE
from pygame.time import Clock, get_ticks
from appdirs import AppDirs

from .constants import SETTINGS, ICON, NOISE, HERO_SPEED, MIDDLE
from .maze import Maze
from .misc import sign, deg, join


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
        self.size = (self.config.getint('Graphics', 'Screen width'),
                     self.config.getint('Graphics', 'Screen height'))
        self.max_fps = self.config.getint('Graphics', 'Maximum FPS')
        self.muted = self.config.getboolean('Sound', 'Muted')
        self.musicvol = self.config.getfloat('Sound', 'Music volume')
        self.touch = self.config.getboolean('Control', 'Touch')
        self.export_dir = self.config.get('Record', 'Directory')
        self.export_rate = self.config.getint('Record', 'Frequency')
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
        for option in ('size', 'max_fps', 'muted', 'musicvol',
                       'touch', 'export_dir', 'export_rate', 'server',
                       'host', 'port', 'timeout', 'headless'):
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
            pygame.mixer.music.load(NOISE)
            pygame.mixer.music.set_volume(config.musicvol)
            pygame.mixer.music.play(-1)
        pygame.display.set_icon(ICON)

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
        self.touch = config.touch
        self.key, self.mouse = config.key, config.mouse
        self.maze = Maze(config.max_fps, config.size, config.headless,
                         config.export_dir, 1000.0 / config.export_rate)
        self.hero = self.maze.hero
        self.clock, self.paused = Clock(), False

    def __enter__(self): return self

    def export_txt(self):
        """Export maze data to string."""
        export = self.maze.update_export(forced=True)
        return '{} {} {} {}\n{}{}{}{}'.format(
            len(export['m']), len(export['e']), len(export['b']), export['s'],
            ''.join(row + '\n' for row in export['m']), join(export['h']),
            ''.join(map(join, export['e'])), ''.join(map(join, export['b'])))

    def update(self):
        """Draw and handle meta events on Pygame window.

        Return False if QUIT event is captured, True otherwise.
        """
        events = pygame.event.get()
        for event in events:
            if event.type == QUIT:
                return False
            elif event.type == VIDEORESIZE:
                self.maze.resize((event.w, event.h))
            elif event.type == KEYDOWN:
                if event.key == self.key['mute']:
                    if pygame.mixer.get_init() is None:
                        pygame.mixer.init(frequency=44100)
                        pygame.mixer.music.load(NOISE)
                        pygame.mixer.music.set_volume(self.musicvol)
                        pygame.mixer.music.play(-1)
                    else:
                        pygame.mixer.quit()
                elif not self.server:
                    if event.key == self.key['new']:
                        self.maze.reinit()
                    elif event.key == self.key['pause'] and not self.hero.dead:
                        self.paused ^= True
            elif event.type == MOUSEBUTTONUP and self.touch:
                # We're careless about which mouse button is clicked.
                maze = self.maze
                if self.hero.dead:
                    maze.reinit()
                else:
                    x, y = pygame.mouse.get_pos()
                    maze.destx, maze.desty = maze.get_grid(x, y)
                    if maze.set_step(maze.isdisplayed):
                        maze.target = maze.get_target(x, y)
                        self.hero.firing = not maze.target.retired
                    if maze.stepx == maze.stepy == 0:
                        maze.destx = maze.desty = MIDDLE

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

    def move(self, x=0, y=0):
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
                data = self.export_txt().encode()
                alpha = deg(self.hero.angle)
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
                # Time is the essence.
                angle = self.hero.angle if angle == alpha else radians(angle)
                self.sockinp = x, y, angle, attack & 1, attack >> 1
                clock.tick(self.fps)
            self.sockinp = 0, 0, -pi * 3 / 4, 0, 0
            new_time = get_ticks()
            print('[{0}] {3}:{4} scored {1} points in {2}ms'.format(
                new_time, self.maze.get_score(), new_time - time, *address))
            connection.close()
            if not self.hero.dead: self.maze.lose()

    def touch_control(self):
        """Handle touch control."""
        maze, hero = self.maze, self.hero
        if maze.target.retired: hero.firing = False
        if hero.firing:
            x, y = maze.get_pos(maze.target.x, maze.target.y)
        else:
            x, y = pygame.mouse.get_pos()
        hero.update_angle(atan2(y - hero.y, x - hero.x))
        self.move()

    def user_control(self):
        """Handle direct control from user's mouse and keyboard."""
        if self.hero.dead: return
        keys = pygame.key.get_pressed()
        buttons = pygame.mouse.get_pressed()

        right = keys[self.key['right']] - keys[self.key['left']]
        down = keys[self.key['down']] - keys[self.key['up']]
        x, y = pygame.mouse.get_pos()
        angle = atan2(y - self.hero.y, x - self.hero.x)

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
        if not self.hero.dead: self.maze.dump_records()
        pygame.quit()


def main():
    """Start game and main loop."""
    # Read configuration file
    dirs = AppDirs(appname='brutalmaze', appauthor=False, multipath=True)
    parents = dirs.site_config_dir.split(pathsep)
    parents.append(dirs.user_config_dir)
    filenames = [pathjoin(parent, 'settings.ini') for parent in parents]
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
        '--touch', action='store_true', default=None,
        help='enable touch-friendly control (fallback: {})'.format(
            config.touch))
    parser.add_argument('--no-touch', action='store_false', dest='touch',
                        help='disable touch-friendly control')
    parser.add_argument(
        '--record-dir', metavar='DIR', dest='export_dir',
        help='directory to write game records (fallback: {})'.format(
            config.export_dir or '*disabled*'))
    parser.add_argument(
        '--record-rate', metavar='SPF', dest='export_rate',
        help='snapshots of game state per second (fallback: {})'.format(
            config.export_rate))
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
        elif config.touch:
            while game.update(): game.touch_control()
        else:
            while game.update(): game.user_control()


# Allow launching the game via invoking ``python -m brutalmaze.game''
if __name__ == '__main__': main()
