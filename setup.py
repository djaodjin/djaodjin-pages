# Copyright (c) 2017, DjaoDjin inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
# TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from distutils.core import setup

import pages

requirements = []
with open('./requirements.txt') as requirements_txt:
    for line in requirements_txt:
        prerequisite = line.split('#')[0].strip()
        if prerequisite:
            requirements += [prerequisite]

setup(
    name='djaodjin-pages',
    version=pages.__version__,
    author='DjaoDjin inc.',
    author_email='support@djaodjin.com',
    install_requires=requirements,
    packages=[
        'pages',
        'pages.api',
        'pages.templatetags',
        'pages.urls',
        'pages.urls.api',
        'pages.urls.views',
        'pages.views'],
    package_data={'pages': [
        'static/css/*', 'static/js/*',
        'static/vendor/css/*', 'static/vendor/js/*',
        'templates/pages/*.html']},
    url='https://github.com/djaodjin/djaodjin-pages/',
    download_url='https://github.com/djaodjin/djaodjin-pages/tarball/%s' \
        % pages.__version__,
    license='BSD',
    description='Pages Django App',
    long_description=open('README.md').read(),
)
