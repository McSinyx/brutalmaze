# characters.py - module for hero and enemy classes
# Copyright (C) 2017-2020  Nguyễn Gia Phong
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

__doc__ = 'Brutal Maze module for hero and enemy classes'

from collections import deque
from math import atan2, gcd, sin, pi
from random import choice, randrange, shuffle
from sys import modules

from .constants import (
    TANGO, HERO_HP, SFX_HEART, HEAL_SPEED, MIN_BEAT, ATTACK_SPEED, ENEMY,
    ENEMY_SPEED, ENEMY_HP, SFX_SPAWN, SFX_SLASH_HERO, MIDDLE, WALL, FIRANGE,
    AROUND_HERO, ADJACENTS, EMPTY, SQRT2, ENEMIES)
from .misc import sign, randsign, regpoly, fill_aapolygon, play
from .weapons import Bullet


class Hero:
    """Object representing the hero.

    Attributes:
        surface (pygame.Surface): the display to draw on
        x, y (int): coordinates of the center of the hero (in pixels)
        angle (float): angle of the direction the hero pointing (in radians)
        color (tuple of pygame.Color): colors of the hero on different HPs
        R (int): circumradius of the regular triangle representing the hero
        next_heal (float): minimum wound in ATTACK_SPEED allowing healing again
        next_beat (float): time until next heart beat (in ms)
        next_strike (float): time until the hero can do the next attack (in ms)
        highness (float): likelihood that the hero shoots toward other angles
        slashing (bool): flag indicating if the hero's doing close-range attack
        firing (bool): flag indicating if the hero is doing long-range attack
        dead (bool): flag indicating if the hero is dead
        spin_speed (float): speed of spinning (in frames per slash)
        spin_queue (float): frames left to finish spinning
        wound (float): amount of wound
        wounds (deque of float): wounds in time of an attack (ATTACK_SPEED)
    """
    def __init__(self, surface, fps, maze_size):
        self.surface = surface
        w, h = maze_size
        self.x, self.y = w >> 1, h >> 1
        self.angle, self.color = -pi * 3 / 4, TANGO['Aluminium']
        self.R = (w * h / sin(pi*2/3) / 624) ** 0.5

        self.next_heal = -1.0
        self.next_beat = self.next_strike = 0.0
        self.highness = 0.0
        self.slashing = self.firing = self.dead = False
        self.spin_speed = fps / HERO_HP
        self.spin_queue = self.wound = 0.0
        self.wounds = deque([0.0])

    def update(self, fps):
        """Update the hero."""
        if self.dead:
            self.spin_queue = 0.0
            return
        old_speed = self.spin_speed
        self.spin_speed = fps / (HERO_HP-self.wound**0.5)
        self.spin_queue *= self.spin_speed / old_speed

        if len(self.wounds) > fps * ATTACK_SPEED / 1000: self.wounds.popleft()
        if sum(self.wounds) < self.next_heal: self.next_heal = -1.0
        self.wound += self.wounds[-1]
        if self.next_heal < 0:
            self.wound -= HEAL_SPEED / self.spin_speed / HERO_HP
            if self.wound < 0: self.wound = 0.0
        self.wounds.append(0.0)
        if self.next_beat <= 0:
            play(SFX_HEART)
            self.next_beat = MIN_BEAT*(2 - self.wound/HERO_HP)
        else:
            self.next_beat -= 1000 / fps
        self.next_strike -= 1000 / fps

        full_spin = pi * 2 / self.sides
        if self.slashing and self.next_strike <= 0:
            self.next_strike = ATTACK_SPEED
            self.spin_queue = randsign() * self.spin_speed
            self.angle -= sign(self.spin_queue) * full_spin
        if round(self.spin_queue) != 0:
            self.angle += sign(self.spin_queue) * full_spin / self.spin_speed
            self.spin_queue -= sign(self.spin_queue)
        else:
            self.spin_queue = 0.0

    @property
    def sides(self):
        """Number of sides the hero has. While the hero is generally
        a trigon, Agent Orange may turn him into a square.
        """
        return 3 if self.next_heal < 0 else 4

    def update_angle(self, angle):
        """Turn to the given angle if the hero is not busy slashing."""
        if round(self.spin_queue) != 0: return
        delta = (angle - self.angle + pi) % (pi * 2) - pi
        unit = pi * 2 / self.sides / self.spin_speed
        if abs(delta) < unit:
            self.angle, self.spin_queue = angle, 0.0
        else:
            self.spin_queue = delta / unit

    @property
    def shots(self):
        """List of Bullet the hero has just shot."""
        if not self.firing or self.slashing or self.next_strike > 0: return []
        self.next_strike = ATTACK_SPEED
        if not randrange(int(self.highness + 1)):
            return [Bullet(self.surface, self.x, self.y,
                           self.angle, 'Aluminium')]
        self.highness -= 1.0
        n = self.sides
        corners = {randrange(n) for _ in range(n)}
        angles = (self.angle + pi*2*corner/n for corner in corners)
        return [Bullet(self.surface, self.x, self.y, angle, 'Aluminium')
                for angle in angles]

    def get_color(self):
        """Return current color of the hero."""
        return self.color[int(self.wound)]

    def draw(self):
        """Draw the hero."""
        trigon = regpoly(self.sides, self.R, self.angle, self.x, self.y)
        fill_aapolygon(self.surface, trigon, self.get_color())

    def resize(self, maze_size):
        """Resize the hero."""
        w, h = maze_size
        self.x, self.y = w >> 1, h >> 1
        self.R = (w * h / sin(pi*2/3) / 624) ** 0.5


class Enemy:
    """Object representing an enemy.

    Attributes:
        maze (Maze): the maze
        x, y (int): coordinates of the center of the enemy (in grids)
        angle (float): angle of the direction the enemy pointing (in radians)
        color (str): enemy's color name
        alive (bool): flag indicating if the enemy is alive
        awake (bool): flag indicating if the enemy is active
        next_strike (float): time until the enemy's next action (in ms)
        move_speed (float): speed of movement (in frames per grid)
        offsetx, offsety (integer): steps moved from the center of the grid
        spin_speed (float): speed of spinning (in frames per slash)
        spin_queue (float): frames left to finish spinning
        wound (float): amount of wound
    """
    def __init__(self, maze, x, y, color):
        self.maze = maze
        self.x, self.y = x, y
        self.angle, self.color = pi / 4, color

        self.alive, self.awake = True, False
        self.next_strike = 0.0
        self.move_speed = self.maze.fps / ENEMY_SPEED
        self.offsetx = self.offsety = 0
        self.spin_speed = self.maze.fps / ENEMY_HP
        self.spin_queue = self.wound = 0.0

    @property
    def pos(self):
        """Coordinates (in pixels) of the center of the enemy."""
        x, y = self.maze.get_pos(self.x, self.y)
        step = self.maze.distance * ENEMY_SPEED / self.maze.fps
        return x + self.offsetx*step, y + self.offsety*step

    @property
    def distance(self):
        """Distance from the center of the enemy
        to the center of the maze.
        """
        return self.maze.get_distance(*self.pos)

    def place(self, x=0, y=0):
        """Move the enemy by (x, y) (in grids)."""
        self.x += x
        self.y += y
        if self.awake: self.maze.map[self.x][self.y] = ENEMY

    @property
    def spawn_volume(self):
        """Volumn of spawning sound effect."""
        return 1 - self.distance / self.maze.get_distance(0, 0) / 2

    def wake(self):
        """Wake the enemy up if it can see the hero.

        Return None if the enemy is already awake, True if the function
        has just woken it, False otherwise.
        """
        if self.awake: return None
        srcx, destx = self.x, MIDDLE
        if abs(destx - srcx) != 1: srcx += sign(destx - srcx) or 1
        srcy, desty = self.y, MIDDLE
        if abs(desty - srcy) != 1: srcy += sign(desty - srcy) or 1
        m, n = destx - srcx, desty - srcy
        lcm = abs(m * n // gcd(m, n))
        w, u = lcm // m, lcm // n
        for i in range(lcm):
            if self.maze.map[srcx+i//w][srcy+i//u] == WALL: return False
        self.awake = True
        self.maze.map[self.x][self.y] = ENEMY
        play(SFX_SPAWN, self.x, self.y)
        return True

    def fire(self):
        """Return True if the enemy has just fired, False otherwise."""
        if self.maze.hero.dead: return False
        x, y = self.pos
        if (self.maze.get_distance(x, y) > FIRANGE*self.maze.distance
            or self.next_strike > 0
            or (self.x, self.y) in AROUND_HERO or self.offsetx or self.offsety
            or randrange((self.maze.hero.slashing+self.maze.isfast()+1) * 3)):
            return False
        self.next_strike = ATTACK_SPEED
        self.maze.bullets.append(
            Bullet(self.maze.surface, x, y, self.get_angle() + pi, self.color))
        return True

    def move(self, speed=ENEMY_SPEED):
        """Return True if it has just moved, False otherwise."""
        if self.offsetx:
            self.offsetx -= sign(self.offsetx)
            return True
        if self.offsety:
            self.offsety -= sign(self.offsety)
            return True
        if self.next_strike > 0: return False

        self.move_speed = self.maze.fps / speed
        directions = [(sign(MIDDLE - self.x), 0), (0, sign(MIDDLE - self.y))]
        shuffle(directions)
        directions.append(choice(ADJACENTS))
        if self.maze.hero.dead: directions = choice(ADJACENTS),
        for x, y in directions:
            if (x or y) and self.maze.map[self.x + x][self.y + y] == EMPTY:
                self.offsetx = round(x * (1 - self.move_speed))
                self.offsety = round(y * (1 - self.move_speed))
                self.maze.map[self.x][self.y] = EMPTY
                self.place(x, y)
                return True
        return False

    def get_slash(self):
        """Return the enemy's close-range damage."""
        wound = (self.maze.slashd - self.distance) / self.maze.hero.R
        return wound if wound > 0 else 0.0

    def slash(self):
        """Return the enemy's close-range damage per frame."""
        wound = self.get_slash() / self.spin_speed
        if self.spin_queue and wound: self.maze.hit_hero(wound, self.color)
        return wound

    def get_angle(self, reversed=False):
        """Return the angle of the vector whose initial point is
        the center of the screen and terminal point is the center of
        the enemy.
        """
        x, y = self.pos
        return atan2(y - self.maze.y, x - self.maze.x)

    def get_color(self):
        """Return current color of the enemy."""
        return TANGO[self.color][int(self.wound)]

    def isunnoticeable(self, x=None, y=None):
        """Return whether the enemy can be noticed.

        Only search within column x and row y if these coordinates
        are provided.
        """
        if x is not None and self.x != x: return True
        if y is not None and self.y != y: return True
        return not self.awake or self.wound >= ENEMY_HP

    def draw(self):
        """Draw the enemy."""
        if self.isunnoticeable(): return
        radius = self.maze.distance / SQRT2
        square = regpoly(4, radius, self.angle, *self.pos)
        fill_aapolygon(self.maze.surface, square, self.get_color())

    def update(self):
        """Update the enemy."""
        if self.awake:
            self.spin_speed, tmp = self.maze.fps / ENEMY_HP, self.spin_speed
            self.spin_queue *= self.spin_speed / tmp
            self.next_strike -= 1000 / self.maze.fps
            if not self.spin_queue and not self.fire() and not self.move():
                self.spin_queue = randsign() * self.spin_speed
                if not self.maze.hero.dead:
                    play(SFX_SLASH_HERO, self.x, self.y, self.get_slash())
            if round(self.spin_queue) != 0:
                self.angle += sign(self.spin_queue) * pi / 2 / self.spin_speed
                self.spin_queue -= sign(self.spin_queue)
            else:
                self.angle, self.spin_queue = pi / 4, 0.0

    def hit(self, wound):
        """Handle the enemy when it's attacked."""
        self.wound += wound

    @property
    def retired(self):
        """Provide compatibility with LockOn object."""
        try:
            return self._retired
        except AttributeError:
            return self.wound >= ENEMY_HP

    @retired.setter
    def retired(self, value):
        self._retired = value

    def die(self):
        """Handle the enemy's death."""
        self.maze.map[self.x][self.y] = EMPTY if self.wake else WALL
        self.alive = False


class Chameleon(Enemy):
    """Object representing an enemy of Chameleon.

    Additional attributes:
        visible (float): time until the Chameleon is visible (in ms)
    """
    def __init__(self, maze, x, y):
        Enemy.__init__(self, maze, x, y, 'Chameleon')
        self.visible = 0.0

    def wake(self):
        """Wake the Chameleon up if it can see the hero."""
        if Enemy.wake(self) is True:
            self.visible = 1000 / ENEMY_SPEED

    def isunnoticeable(self, x=None, y=None):
        """Return whether the enemy can be noticed.

        Only search within column x and row y if these coordinates
        are provided.
        """
        return (Enemy.isunnoticeable(self, x, y)
                or self.visible <= 0 and not self.spin_queue
                and self.maze.next_move <= 0)

    def update(self):
        """Update the Chameleon."""
        Enemy.update(self)
        if self.awake: self.visible -= 1000 / self.maze.fps

    def hit(self, wound):
        """Handle the Chameleon when it's attacked."""
        self.visible = 1000.0 / ENEMY_SPEED
        Enemy.hit(self, wound)


class Plum(Enemy):
    """Object representing an enemy of Plum."""
    def __init__(self, maze, x, y):
        Enemy.__init__(self, maze, x, y, 'Plum')

    def clone(self, other):
        """Turn the other enemy into a clone of this Plum and return
        True if that enemy is also a Plum, otherwise return False.
        """
        if other.color != 'Plum': return False
        other.x, other.y, other.angle = self.x, self.y, self.angle
        other.awake, other.next_strike = True, self.next_strike
        other.offsetx, other.offsety = self.offsetx, self.offsety
        other.spin_queue, other.wound = self.spin_queue, self.wound
        return True


class ScarletRed(Enemy):
    """Object representing an enemy of Scarlet Red."""
    def __init__(self, maze, x, y):
        Enemy.__init__(self, maze, x, y, 'ScarletRed')

    def fire(self):
        """Scarlet Red doesn't shoot."""
        return False

    def move(self):
        return Enemy.move(self, ENEMY_SPEED * SQRT2)

    def slash(self):
        """Handle the Scarlet Red's close-range attack."""
        self.wound -= Enemy.slash(self)
        if self.wound < 0: self.wound = 0.0


def new_enemy(maze, x, y):
    """Return an enemy of a random type in the grid (x, y)."""
    color = choice(ENEMIES)
    try:
        return getattr(modules[__name__], color)(maze, x, y)
    except AttributeError:
        return Enemy(maze, x, y, color)
