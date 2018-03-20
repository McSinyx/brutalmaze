#!/usr/bin/env python3
from math import inf, atan2, degrees
from socket import socket
from random import randint

clientsocket = socket()
clientsocket.connect(('localhost', 8089))
while True:
    length = clientsocket.recv(7).decode()
    if length in ('', '0000000'): break     # connection closed or game over
    l = clientsocket.recv(int(length)).decode().split()
    data = iter(l)
    nh, ne, nb, score = (int(next(data)) for _ in range(4))
    maze = [[bool(int(i)) for i in next(data)] for _ in range(nh)]
    hp = (lambda c: 0 if c == 48 else 123 - c)(ord(next(data)))
    hx, hy, ha = (int(next(data)) for _ in range(3))
    attackable, mobility = (bool(int(next(data))) for _ in range(2))

    shortest = angle = inf
    for _ in range(ne):
        p = (lambda c: 0 if c == 48 else 3 - (c-97)%3)(ord(next(data)))
        x, y, a = (int(next(data)) for _ in range(3))
        d = ((x - hx)**2 + (y - hy)**2)**0.5
        if d < shortest:
            shortest = d
            b = degrees(atan2(y - hy, x - hx))
            angle = round(b + 360 if b < 0 else b)
    # calculate to dodge from bullets is a bit too much for an example

    move = 4 if ne and hp > 2 else 0
    if angle == inf:
        angle, attack = ha, 0
    elif not attackable:
        attack = 0
    elif shortest < 160 or hp < 3:
        move, angle, attack = 8, ha, 2
    else:
        attack = 1
    clientsocket.send('{} {} {}'.format(move, angle, attack).encode())
clientsocket.close()
