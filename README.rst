Brutal Maze
===========

Brutal Maze is a hack and slash game with fast-paced action and a minimalist
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
  Now you can launch the game by running the command ``brutalmaze``.

For more information, see the `Installation <https://github.com/McSinyx/brutalmaze/wiki/Installation>`_
from Brutal Maze wiki.

Configuration
-------------

Brutal Maze supports both configuration file and command-line options.
Apparently one can change settings for graphics and control in the config file
and set graphics options using in CLI. These settings are read in the following
order:

0. Default configuration [0]_
1. System-wide configuration file [1]_
2. Local configuration file [1]_
3. Manually set configuration file [2]_
4. Command-line arguments

The later-read preferences will overide the previous ones.

.. [0] This can be copied to desired location by ``brutalmaze --write-config
   PATH``. ``brutalmaze --write-config`` alone will print the file to stdout.
.. [1] These will be listed as fallback config in the help message
   (``brutalmaze --help``). See `wiki <https://github.com/McSinyx/brutalmaze/wiki/Configuration>`_
   for more info.
.. [2] If specified by ``brutalmaze --config PATH``.
