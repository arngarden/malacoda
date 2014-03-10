# -*- coding: utf-8 -*-

from setuptools import setup

longdesc = """
This is a library for creating Daemons that can communicate with each other using ZeroMQ
and save persistant data on disc.
"""

setup(
    name = 'malacoda',
    packages = ['malacoda'],
    version = '0.1',
    description = 'Daemon framework with communication and persistant storage capabilities',
    author='Gustav Arngården',
    author_email = 'arngarden@gmail.com',
    url = 'https://github.com/arngarden/malacoda/',
    license = 'Apache Software License',
    classifiers = ['Programming Language :: Python',
                   'Operating System :: MacOS',
                   'Operating System :: POSIX',
                   'Development Status :: 4 - Beta',
                   'Intended Audience :: Developers',
                   'Intended Audience :: System Administrators',
                   'License :: OSI Approved :: Apache Software License',
                   'Topic :: Internet :: WWW/HTTP',
                   'Topic :: Software Development',
                   'Topic :: System :: Networking',
                   'Topic :: System :: Systems Administration'
                   ],
    long_description = longdesc,
    install_requires = ['psutil']
)
