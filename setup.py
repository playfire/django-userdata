#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name='django-userdata',
    description="Helper to manage one-to-one User-specific Django models.",
    version='0.1',
    url='http://code.playfire.com/',

    author='Playfire.com',
    author_email='tech@playfire.com',
    license='BSD',

    packages=find_packages(),
)
