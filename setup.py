#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import find_packages, setup
from os.path import join, dirname

from odoo.release import version, description, long_desc, url, author, author_email, classifiers
from odoo.service.db import database_identifier

exec(open(join(dirname(__file__), 'odoo', 'release.py'), 'rb').read())  # Load release variables
lib_name = 'odoo'

setup(
    name='odoo',
    version="1.0",
    description="Luminous Odoo",
    long_description="Luminous Odoo ERP",
    url="https://www.luminouslabsbd.com",
    author="Luminouslabsbd",
    author_email="support@luminouslabsbd.com",
    classifiers=[c for c in classifiers.split('\n') if c],
    license=license,
    scripts=['setup/odoo'],
    packages=find_packages(),
    package_dir={'%s' % lib_name: 'odoo'},
    include_package_data=True,
    install_requires=[
        'asn1crypto',
        'babel >= 1.0',
        'cbor2',
        'chardet',
        'cryptography',
        'decorator',
        'docutils',
        'geoip2',
        'gevent',
        'greenlet',
        'idna',
        'Jinja2',
        'lxml',  # windows binary http://www.lfd.uci.edu/~gohlke/pythonlibs/
        'libsass',
        'MarkupSafe',
        'num2words',
        'ofxparse',
        'openpyxl',
        'passlib',
        'pillow',  # windows binary http://www.lfd.uci.edu/~gohlke/pythonlibs/
        'polib',
        'psutil',  # windows binary code.google.com/p/psutil/downloads/list
        'psycopg2 >= 2.2',
        'pyopenssl',
        'PyPDF2',
        'pyserial',
        'python-dateutil',
        'python-stdnum',
        'pytz',
        'pyusb >= 1.0.0b1',
        'qrcode',
        'reportlab',  # windows binary pypi.python.org/pypi/reportlab
        'rjsmin',
        'requests',
        'urllib3',
        'vobject',
        'werkzeug',
        'xlrd',
        'xlsxwriter',
        'xlwt',
        'zeep',
    ],
    python_requires='>=3.10',
    extras_require={
        'ldap': ['python-ldap'],
    },
    tests_require=[
        'freezegun',
    ],
)
