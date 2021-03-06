from setuptools import setup, find_packages

import os
import sys

py_version = sys.version_info[:2]
if not (3, 5) < py_version < (3, 9):
    raise RuntimeError('Taskmaster needs Python version 3.6 - 3.8 to run')

dist = setup(
    name='taskmaster',
    version='1.0.0',
	url='https://github.com/Rouhija/Taskmaster',
	description="A system for controlling process state under UNIX (inspired by Supervisor)",
    author="Sami Rouhe",
    author_email="rouhesami@gmail.com",
	packages=find_packages(),
    test_suite="taskmaster.tests",
    install_requires=['PyYAML'],
    entry_points={
        'console_scripts': [
			'taskmasterd = taskmaster.taskmasterd:main',
            'taskmasterctl = taskmaster.taskmasterctl:main',
        ],
    }
)