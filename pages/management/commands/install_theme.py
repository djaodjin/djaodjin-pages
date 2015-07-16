# Copyright (c) 2015, Djaodjin Inc.
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

import logging, os, zipfile
from optparse import make_option

from django.core.management.base import BaseCommand

from ...themes import install_theme

LOGGER = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Install resources and templates into a multi-tier environment.

    Templates are installed into ``MULTITIER_TEMPLATES_ROOT/APP_NAME``.
    Resources include CSS, JS, images and other files which can be accessed
    anonymously over HTTP and are necessary for the functionality of the site.
    They are copied into ``MULTITIER_RESOURCES_ROOT/APP_NAME``
    """

    option_list = BaseCommand.option_list + (
        make_option('--app_name', action='store', dest='app_name',
            default=None, help='overrides the destination theme name'),
        )

    def handle(self, *args, **options):
        for package_path in args:
            app_name = options['app_name']
            if not app_name:
                app_name = os.path.splitext(os.path.basename(package_path))[0]
            print "install %s to %s" % (package_path, app_name)
            with zipfile.ZipFile(package_path, 'r') as zip_file:
                install_theme(app_name, zip_file)
