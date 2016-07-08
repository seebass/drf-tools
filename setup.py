# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

setup(
    name='drf-tools',
    version="0.9.25",
    url='https://github.com/seebass/drf-tools',
    license='MIT',
    description='Multiple extensions and test utilities for Django REST Framework 3',
    author='Sebastian Bredehöft',
    author_email='bredehoeft.sebastian@gmail.com',
    packages=find_packages(exclude=['tests*']),
    install_requires=[
        'django>=1.8',
        'djangorestframework>=3.0.0',
        'drf-nested-fields>=0.9.0',
        'drf-hal-json>=0.9.0',
        'drf-enum-field>=0.9.0',
        'drf-nested-routing>=0.9.0',
        'django-filter>=0.10.0',
        'openpyxl>=2.2.5',
        'chardet>=2.3.0'
    ],
    zip_safe=False,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Topic :: Internet :: WWW/HTTP',
    ]
)
