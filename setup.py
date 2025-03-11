#!/usr/bin/env python
"""
Setup script for Wikly.
"""

from setuptools import setup, find_packages
import os

# Read the version from __init__.py
with open(os.path.join('wikly', '__init__.py'), 'r') as f:
    for line in f:
        if line.startswith('__version__'):
            version = line.split('=')[1].strip().strip("'\"")
            break
    else:
        version = '0.1.0'

# Read long description from README.md
with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='wikly',
    version=version,
    description='A tool to export and analyze Wiki.js content with AI capabilities',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Wikly Contributors',
    author_email='baristovnik@gmail.com',
    url='https://github.com/barisgit/wikly',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'requests>=2.25.0',
        'click>=8.0.0',
        'python-dotenv>=0.15.0',
        'pathlib>=1.0.1',
        'pyyaml>=6.0.1',
        'markdown>=3.7.0',
    ],
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'pytest-mock>=3.10.0',
            'pytest-cov>=4.0.0',
            'pytest-asyncio>=0.21.0',
        ],
    },
    entry_points={
        'console_scripts': [
            'wikly=wikly.cli:cli',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Topic :: Utilities',
    ],
    python_requires='>=3.8',
    keywords='wiki, wiki.js, export, analyze, ai, style-guide, content-management',
) 