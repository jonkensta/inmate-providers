"""
pymates setup.py
"""

from setuptools import setup, find_packages

with open('README.md') as infile:
    README = infile.read()

with open('LICENSE') as infile:
    LICENSE = infile.read()

setup(
    name='pymates',
    version='0.2.0',
    description='Module for programatically finding Texas inmates',
    long_description=README,
    author='Jonathan Starr',
    url='https://github.com/jonkensta/inmate-providers',
    license=LICENSE,
    packages=find_packages(),
    install_requires=['bs4', 'aiohttp', 'nameparser'],
)
