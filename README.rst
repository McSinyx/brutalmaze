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

Brutal Maze has a few notable features:

* Being highly portable.
* Auto-generated and infinite maze.
* No binary data for drawing.
* Enemies with special abilities: stun, poison, camo, etc.
* Somewhat a realistic physic and logic system.
* Resizable game window in-game.
* Easily customizable via INI file format.
* Remote control through TCP/IP socket (can be used in AI researching).

Installation
------------

Brutal Maze is written in Python and is compatible with both version 2 and 3.
The installation procedure should be as simple as follows:

* Install Python and `pip <https://pip.pypa.io/en/latest/>`_. Make sure the
  directory for `Python scripts <https://docs.python.org/2/install/index.html#alternate-installation-the-user-scheme>`_
  is in your ``$PATH``.
* Open Terminal or Command Prompt and run ``pip install --user brutalmaze``.

For more information, see
`Installation <https://github.com/McSinyx/brutalmaze/wiki/Installation>`_
page from Brutal Maze wiki.

After installation, you can launch the game by running the command
``brutalmaze``. Below are default bindings:

F2
   New game.
``p``
   Toggle pause.
``m``
   Toggle mute.
Left
   Move left.
Right
   Move right.
Up
   Move up.
Down
   Move down.
Left Mouse
   Long-range attack.
Right Mouse
   Close-range attack, also dodge from bullets.

Configuration
-------------

Brutal Maze supports both configuration file and command-line options.
Apparently, while settings for graphics, sound and socket server can be set
either in the config file or using CLI, keyboard and mouse bindings are limited
to configuration file only.

Settings are read in the following order:

0. Default configuration [0]_
1. System-wide configuration file [1]_
2. Local configuration file [1]_
3. Manually set configuration file [2]_
4. Command-line arguments

Later-read preferences will override previous ones.

Remote control
--------------

If you enable the socket server [3]_, Brutal Maze will no longer accept direct
input from your mouse or keyboard, but wait for a client to connect. Details
about I/O format are explained carefully in
`Remote control <https://github.com/McSinyx/brutalmaze/wiki/Remote-control>`_
wiki page.

License
-------

Brutal Maze's source code and its icon are released under GNU Affero General
Public License version 3 or later. This means if you run a modified program on
a server and let other users communicate with it there, your server must also
allow them to download the source code corresponding to the modified version
running there.

This project also uses Tango color palette and several sound effects, whose
authors and licenses are listed in
`Credits <https://github.com/McSinyx/brutalmaze/wiki/Credits>`_ wiki page.

.. [0] This can be copied to desired location by ``brutalmaze --write-config
   PATH``. ``brutalmaze --write-config`` alone will print the file to stdout.
.. [1] These will be listed as fallback config in the help message
   (``brutalmaze --help``). See `wiki <https://github.com/McSinyx/brutalmaze/wiki/Configuration>`_
   for more info.
.. [2] If specified by ``brutalmaze --config PATH``.
.. [3] This can be done by either editing option *Enable* in section *Server*
   in the configuration file, or launching Brutal Maze using ``brutalmaze
   --server``.
