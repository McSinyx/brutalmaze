#!/usr/bin/env python
# -*- coding: utf-8 -*-
from setuptools import setup

with open('README.rst') as f:
    long_description = f.read()

setup(
    name='brutalmaze',
    version='0.7.8',
    description='A minimalist TPS game with fast-paced action',
    long_description=long_description,
    url='https://github.com/McSinyx/brutalmaze',
    author='Nguyễn Gia Phong',
    author_email='vn.mcsinyx@gmail.com',
    license='GPLv3+',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: MacOS X',
        'Environment :: Win32 (MS Windows)',
        'Environment :: X11 Applications',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Games/Entertainment :: Arcade'],
    keywords='pygame third-person-shooter arcade-game maze ai-challenges',
    packages=['brutalmaze'],
    install_requires=['appdirs', 'pygame>=1.9'],
    package_data={'brutalmaze': ['icon.png', 'soundfx/*.ogg', 'settings.ini']},
    entry_points={'console_scripts': ['brutalmaze = brutalmaze.game:main']})
