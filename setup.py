#
# SetupTools script for nevis
#
from setuptools import setup, find_packages


# Get version number
import os
import sys
sys.path.append(os.path.abspath('nevis'))
from _nevis_version import __version__ as version  # noqa
sys.path.pop()
del(os, sys)


# Load text for long description
with open('README.md') as f:
    readme = f.read()


# Go!
setup(
    # See https://python-packaging.readthedocs.io/en/latest/index.html
    # for details of what goes in here.

    # Module name (lowercase)
    name='nevis',

    # Version
    version=version,

    # Description
    description=('Presents the landscape of Great Britain as a testbed for'
                 ' optimisation and sampling methods.'),
    long_description=readme,
    long_description_content_type='text/markdown',

    # Author and license
    license='BSD 3-clause license',
    author='The Where Is Ben Nevis team',
    author_email='michael.clerx@nottingham.ac.uk',

    # Project URLs (only first is required, rest is for PyPI)
    url='https://github.com/CardiacModelling/BenNevis',
    project_urls={
        'Bug Tracker': 'https://github.com/CardiacModelling/BenNevis/issues',
        #'Documentation': 'http://docs.myokit.org',
        'Source Code': 'https://github.com/CardiacModelling/BenNevis',
    },

    # Classifiers for pypi
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Topic :: Scientific/Engineering',
        'Topic :: Scientific/Engineering :: Mathematics',
    ],

    # Packages to include
    packages=find_packages(include=('nevis', 'nevis.*')),

    # Include non-python files (via MANIFEST.in)
    include_package_data=True,

    # List of dependencies
    install_requires=[
        'bnglonlat',
        'matplotlib>=1.5',
        'numpy',
        'scipy',
        'setuptools',
        'zipfile-deflate64',
    ],

    # Optional extras
    extras_require={
        'dev': [
            #'coverage',                 # Coverage checking
            'flake8>=3',                # Style checking
            #'sphinx>=1.5, !=1.7.3',     # Doc generation
        ],
        'extras': [
            'convertbng',       # Accurate version of bnglonlat
            'pillow',           # To check generated image sizes (PIL)
        ],
    },
)
