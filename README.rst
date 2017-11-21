Brutal Maze
===========

Brutal Maze is a hash and slash game with fast-paced action and a minimalist
art style.

.. image:: https://raw.githubusercontent.com/McSinyx/brutalmaze/master/screenshot.png

The game features a trigon trapped in an infinite maze. As our hero tries to
escape, the maze's border turns into aggressive squares trying to stop him.
Your job is to help the trigon fight against those evil squares and find a way
out (if there is any). Be aware that the more get killed, the more will show up
and our hero will get weaker when wounded.

Brutal Maze has a few notable feautures:

* Being highly portable.
* Auto-generated and infinite maze.
* No binary data for drawing.
* Enemies with special abilities: stun, poison, camo, etc.
* Somewhat a realistic physic and logic system.
* Resizable game window in-game.

Installation
------------

Brutal Maze is written in Python and is compatible with both version 2 and 3.
The installation procedure should be as simply as follow:

* Install Python and `pip <https://pip.pypa.io/en/latest/>`_. Make sure the
  directory for `Python scripts <https://docs.python.org/2/install/index.html#alternate-installation-the-user-scheme>`_
  is in your ``$PATH``.
* Open Terminal or Command Prompt and run ``pip install --user brutalmaze``.
  Now you can lauch the game by running the command ``brutalmaze``.

For more information, see the `Installation <https://github.com/McSinyx/brutalmaze/wiki/Installation>`_
from Brutal Maze wiki.

Control
-------

F2
   New game.
Escape, ``p``
   Pause.
Up, ``w``
   Move up.
Down, ``s``
   Move down.
Left, ``a``
   Move left.
Right, ``d``
   Move right.
Left Mouse
   Long-range attack.
Return, Right Mouse
   Close-range attack, also dodge from bullets.
