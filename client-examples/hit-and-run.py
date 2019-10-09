#!/usr/bin/env python3
from math import inf, atan2, degrees
from random import randrange
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


clientsocket = socket()
clientsocket.connect(('localhost', 8089))
corners, sides = [0, 2, 6, 8], [1, 3, 5, 7]
around, move = [0, 1, 2, 3, 5, 6, 7, 8], 4
while True:
    length = clientsocket.recv(7).decode()
    if length in ('', '0000000'): break     # connection closed or game over
    data = iter(clientsocket.recv(int(length)).decode().split())
    nh, ne, nb, score = (int(next(data)) for _ in range(4))
    maze = [list(next(data)) for _ in range(nh)]
    hp = (lambda c: 0 if c == 48 else 123 - c)(ord(next(data)))
    hx, hy, ha = (int(next(data)) for _ in range(3))
    attackable, heal = (bool(int(next(data))) for _ in range(2))

    if nh:
        moves = get_moves(len(maze) // 2, len(maze[0]) // 2)
        if move == 4 or is_wall(maze, *moves[move]):
            try:
                idx = AROUND.index(move)
            except ValueError:
                pass
            else:
                around.sort(key=(lambda i: (lambda x: min(x, 8 - x))(
                    abs(AROUND.index(i) - idx))))
            for move in around:
                idx = AROUND.index(move)
                if all(map(
                    (lambda i: not is_wall(maze, *moves[i])),
                    (move, AROUND[idx - 1], AROUND[idx - 7]))):
                    break
            else:
                move = 4

    angle, shortest = ha, inf
    for _ in range(ne):
        p = 3 - (ord(next(data)) - 97)%3
        x, y, a = (int(next(data)) for _ in range(3))
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
    clientsocket.send('{} {} {}'.format(move, angle, attack).encode())
clientsocket.close()
