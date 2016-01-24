#!/usr/bin/env python3
# written by Daniel Oaks <daniel@danieloaks.net>
# Released under the ISC license

from setuptools import setup, find_packages

with open('README.rst') as file:
    long_description = file.read()

setup(
    name='girc',
    version='0.2.1',
    description='A modern Python IRC library for Python 3.4, based on asyncio. In Development.',
    long_description=long_description,
    author='Daniel Oaks',
    author_email='daniel@danieloaks.net',
    url='https://github.com/DanielOaks/girc',
    packages=find_packages(),
    scripts=['girc_test'],
    install_requires=['docopt'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: ISC License (ISCL)',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Communications :: Chat',
        'Topic :: Communications :: Chat :: Internet Relay Chat',
    ]
)
