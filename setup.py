from setuptools import setup, find_packages

from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.org'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='sosachkino',
    version='0.1',

    description='Web-based sosach webm viewer',
    long_description=long_description,

    author='Vladimir Gorbunov',
    author_email='vsg@suburban.me',

    packages=find_packages(exclude=['docs', 'tests']),
    install_requires=[
        'aiohttp',
        'aiohttp_jinja2',
        'aiopg[sa]',
    ],

    extras_require = {
        'testing': [
            'WebTest >= 1.3.1',  # py3 compat
            'pytest',
            'pytest-cov',
        ]
    },
    entry_points = {
        'console_scripts': [
            'sosachkino=sosachkino:main',
            'sosachkino-initdb=sosachkino.db.initdb:initdb',
            'sosachkino-printsql=sosachkino.db.initdb:print_sql'
        ],
    },

    include_package_data=True,
)
