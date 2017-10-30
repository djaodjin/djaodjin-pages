# Copyright (c) 2017, Djaodjin Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os, shutil, tempfile, zipfile

from django.core.management.base import BaseCommand
from django.core.files.storage import FileSystemStorage
import requests
from storages.backends.s3boto import S3BotoStorage

from ...themes import install_theme

#pylint:disable=no-name-in-module,import-error
from django.utils.six.moves.urllib.parse import urlparse


class Command(BaseCommand):
    """
    Install resources and templates into a multi-tier environment.

    Templates are installed into ``THEMES_DIR/APP_NAME/templates/``.
    Resources include CSS, JS, images and other files which can be accessed
    anonymously over HTTP and are necessary for the functionality of the site.
    They are copied into ``PUBLIC_ROOT/APP_NAME``
    """

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument('--force',
            action='store_true', dest='force', default=False,
            help='overwrite existing directories and files')
        parser.add_argument('--app_name',
            action='store', dest='app_name', default=None,
            help='overrides the destination theme name')
        parser.add_argument('packages', nargs='*',
            help='list of theme packages')

    def handle(self, *args, **options):
        app_name = options['app_name']
        for package_path in options['packages']:
            parts = urlparse(package_path)
            package_file = None
            try:
                if parts.scheme == 's3':
                    basename = os.path.basename(parts.path)
                    package_storage = S3BotoStorage(bucket_name=parts.netloc,
                        location=os.path.dirname(parts.path))
                    package_file = package_storage.open(basename)
                elif parts.scheme in ['http', 'https']:
                    basename = os.path.basename(parts.path)
                    resp = requests.get(package_path, stream=True)
                    if resp.status_code == 200:
                        package_file = tempfile.NamedTemporaryFile()
                        shutil.copyfileobj(resp.raw, package_file)
                        package_file.seek(0)
                    else:
                        raise RuntimeError(
                            "requests status code: %d" % resp.status_code)
                else:
                    basename = os.path.basename(package_path)
                    #pylint:disable=redefined-variable-type
                    package_storage = FileSystemStorage(
                        os.path.dirname(package_path))
                    package_file = package_storage.open(basename)
                if not options['app_name']:
                    app_name = os.path.splitext(basename)[0]
                self.stdout.write("install %s to %s\n" % (
                    package_path, app_name))
                with zipfile.ZipFile(package_file, 'r') as zip_file:
                    install_theme(app_name, zip_file, force=options['force'])
            finally:
                if hasattr(package_file, 'close'):
                    package_file.close()
