#!/usr/bin/env python

from setuptools import setup

setup(name='txjason',
      version='0.1.0',
      description='jsonrpc 2.0 module',
      author='Flowroute LLC',
      author_email='matthew@flowroute.com',
      packages=['txjason'],
      install_requires=[
          'jsonrpcbase',
      ],
)
