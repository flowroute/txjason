from setuptools import setup

setup(name='txjason',
      version='0.1.0',
      description='Twisted jsonrpc 2.0 module',
      author='Flowroute Inc.',
      author_email='development@flowroute.com',
      url='https://github.com/flowroute/txjason',
      packages=['txjason'],
      install_requires=[
          'Twisted',
      ],
)
