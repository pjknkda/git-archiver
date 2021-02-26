import re
from os import path

from setuptools import setup

wdir = path.abspath(path.dirname(__file__))

with open(path.join(wdir, 'git_archiver.py'), encoding='utf-8') as f:
    try:
        version = re.findall(r"^__version__ = '([^']+)'\r?$",
                             f.read(), re.M)[0]
    except IndexError:
        raise RuntimeError('Unable to determine version.')

with open(path.join(wdir, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='git-archiver',
    version=version,
    description='A simple webserver to make an archive for git repository under the quota limitation.',
    long_description=long_description,
    keywords='git docker',

    author='Jungkook Park',
    author_email='jk@elicer.com',
    url='https://github.com/pjknkda/git-archive',
    license='MIT',

    python_requires='>=3.7',
    install_requires=[
        'aiohttp==3.7.4',
        'docker==4.0.2'
    ],

    py_modules=['git_archiver'],

    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3 :: Only',
    ]
)
