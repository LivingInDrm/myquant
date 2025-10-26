#coding: utf-8

from setuptools import setup, find_packages

setup(
    name='rqalpha-mod-xt-source',
    version='0.1.0',
    description='QMT data source module for RQAlpha',
    packages=find_packages(),
    author='Your Name',
    author_email='your.email@example.com',
    license='Apache License v2',
    package_data={'': ['*.*']},
    url='https://github.com/yourusername/rqalpha-mod-xt-source',
    install_requires=[
        'rqalpha',
    ],
    zip_safe=False,
    classifiers=[
        'Programming Language :: Python :: 3',
        'Operating System :: Microsoft :: Windows',
    ],
)
