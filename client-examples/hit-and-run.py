#!/usr/bin/env python3
from contextlib import closing, suppress
from math import inf, atan2, degrees
from random import randrange, shuffle
from socket import socket

AROUND = [5, 2, 1, 0, 3, 6, 7, 8]


def get_moves(y, x):
    """Return tuple of encoded moves."""
    return ((y - 1, x - 1), (y - 1, x), (y - 1, x + 1),
            (y,     x - 1), (y,     x), (y,     x + 1),
            (y + 1, x - 1), (y + 1, x), (y + 1, x + 1))


def is_wall(maze, y, x):
    """Return weather the cell (x, y) is wall."""
    return maze[y][x] != '0'


def get_move(maze, move):
    """Return an outstanding move."""
    moves, around = get_moves(len(maze) // 2, len(maze[0]) // 2), AROUND[:]
    if move != 4 and not is_wall(maze, *moves[move]): return move
    if move == 4:
        shuffle(around)
    else:
        idx = AROUND.index(move)
        around.sort(key=lambda i: abs(abs(abs(AROUND.index(i)-idx)-4)-4))
    for move in around:
        idx = AROUND.index(move)
        if all(not is_wall(maze, *moves[i])
               for i in (move, AROUND[idx - 1], AROUND[idx - 7])):
            return move
    return 4


with suppress(KeyboardInterrupt), closing(socket()) as sock:
    sock.connect(('localhost', 42069))
    move = 4
    while True:
        length = sock.recv(7).decode()
        # connection closed or game over
        if length in ('', '0000000'): break
        data = iter(sock.recv(int(length)).decode().split())
        nh, ne, nb, score = (int(next(data)) for i in range(4))
        maze = [list(next(data)) for i in range(nh)]
        hp = (lambda c: 0 if c == 48 else 123 - c)(ord(next(data)))
        hx, hy, ha = (int(next(data)) for i in range(3))
        attackable, heal = (bool(int(next(data))) for i in range(2))

        if nh: move = get_move(maze, move)
        angle, shortest = ha, inf
        for i in range(ne):
            p = 3 - (ord(next(data)) - 97)%3
            x, y, a = (int(next(data)) for j in range(3))
            d = ((x - hx)**2 + (y - hy)**2)**0.5
            if d < shortest:
                shortest = d
                b = degrees(atan2(y - hy, x - hx))
                angle = round(b + 360 if b < 0 else b)

        if hp <= 2 and heal:
            move, attack = 4, 2
        elif not ne:
            attack = randrange(3) * (attackable and hp > 2)
        elif shortest < 160:
            move, angle, attack = AROUND[round(angle/45 - 0.5) - 4], ha, 2
        else:
            attack = 1
        sock.send(f'{move} {angle} {attack}'.encode())
