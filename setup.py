#!/usr/bin/env python
from setuptools import setup, find_packages
from setuptools.extension import Extension
from Cython.Build import cythonize

util_ext = Extension(
    name='dc.util',
    sources=['dc/primes/primes.c', 'dc/util.pyx'],
    include_dirs=['dc/primes/'],
)

setup(name='dc',
      version='0.3',
      description='Portable parser for Disney\'s Distributed Class protocol',
      author='alexanderr',
      url='https://www.github.com/alexanderr/pydc',
      ext_modules=cythonize(util_ext),
      packages=['dc'],
      requires=['Cython'],
      package_data={"": ["*.lark"]},
)
