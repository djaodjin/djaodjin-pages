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

import logging, os

from django.conf import settings as django_settings
from django.utils._os import safe_join

from . import settings

LOGGER = logging.getLogger(__name__)


def install_theme(theme_name, zip_file):
    """
    Extract resources and templates from an opened ``ZipFile``
    and install them at a place they can be picked by the multitier
    logic in ``template_loader.Loader.get_template_sources``.
    """
    LOGGER.info("install theme %s", theme_name)
    static_dir = safe_join(os.path.dirname(django_settings.APP_STATIC_ROOT),
        theme_name)
    templates_dir = safe_join(django_settings.TEMPLATE_DIRS[0], theme_name)
    extracts = []
    for name in zip_file.namelist():
        full_path = None
        test_parts = safe_join(static_dir, name).replace(
            static_dir + os.sep, '').split(os.sep)[1:] # remove topdir
        base = test_parts.pop(0)
        if base == 'public':
            if settings.PUBLIC_WHITELIST is not None:
                if os.path.join(*test_parts) in settings.PUBLIC_WHITELIST:
                    full_path = safe_join(static_dir, *test_parts)
            else:
                full_path = safe_join(static_dir, *test_parts)
        elif base == 'templates':
            if settings.TEMPLATES_WHITELIST is not None:
                if os.path.join(*test_parts) in settings.TEMPLATES_WHITELIST:
                    full_path = safe_join(templates_dir, *test_parts)
            else:
                full_path = safe_join(templates_dir, *test_parts)
        if full_path and not os.path.isdir(os.path.dirname(full_path)):
            extracts += [(name, full_path)]

    for name, full_path in extracts:
        if not os.path.isdir(os.path.dirname(full_path)):
            os.makedirs(os.path.dirname(full_path))
        with open(full_path, 'wb') as extracted_file:
            extracted_file.write(zip_file.read(name))
