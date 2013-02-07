#!/usr/bin/env python

from setuptools import setup

setup(name='txjsonrpc2',
      version='0.1.0',
      description='jsonrpc 2.0 module',
      author='Flowroute LLC',
      author_email='matthew@flowroute.com',
      packages=['txjsonrpc2'],
      install_requires=[
          'jsonrpcbase',
      ],
)
