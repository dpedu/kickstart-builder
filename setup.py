#!/usr/bin/env python3
from setuptools import setup

__version__ = "0.0.1"

setup(name='isoserver',
      version=__version__,
      description='',
      url='http://git.davepedu.com/dave/kickstart-builder',
      author='dpedu',
      author_email='dave@davepedu.com',
      packages=['isoserver'],
      entry_points={
          "console_scripts": [
              "isoserverd = isoserver:main"
          ]
      },
      include_package_data=True,
      package_data={'isoserver': ['main.html']},
      zip_safe=False)
