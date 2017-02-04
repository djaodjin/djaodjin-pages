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

import logging, os, shutil, tempfile

from django.core.exceptions import PermissionDenied
from django.utils._os import safe_join
from django.utils import six

from . import settings

LOGGER = logging.getLogger(__name__)


def get_theme_dir(theme_name):
    if isinstance(settings.THEME_DIR_CALLABLE, six.string_types):
        from ..compat import import_string
        settings.THEME_DIR_CALLABLE = import_string(
            settings.THEME_DIR_CALLABLE)
    theme_dir = settings.THEME_DIR_CALLABLE(theme_name)
    return theme_dir


def install_theme(theme_name, zip_file, force=False):
    """
    Extract resources and templates from an opened ``ZipFile``
    and install them at a place they can be picked by the multitier
    logic in ``template_loader.Loader.get_template_sources``.
    """
    #pylint:disable=too-many-statements,too-many-locals
    LOGGER.info("install theme %s%s", theme_name, " (force)" if force else "")
    theme_dir = get_theme_dir(theme_name)
    public_dir = safe_join(settings.PUBLIC_ROOT, theme_name)
    templates_dir = safe_join(theme_dir, 'templates')

    if not force and os.path.exists(public_dir):
        LOGGER.warning("install theme '%s' but '%s' already exists.",
            theme_name, public_dir)
        raise PermissionDenied("Theme public assets already exists.")

    if not force and os.path.exists(templates_dir):
        LOGGER.warning("install theme '%s' but '%s' already exists.",
            theme_name, templates_dir)
        raise PermissionDenied("Theme templates already exists.")

    # We rely on the assumption that ``public_dir`` and ``templates_dir``
    # are on the same filesystem. We create a temporary directory on that
    # common filesystem, which guarentees that:
    #   1. If the disk is full, we will find on extract, not when we try
    #      to move the directory in place.
    #   2. If the filesystem is encrypted, we don't inadvertently leak
    #      information by creating "temporary" files.
    tmp_base = safe_join(
        os.path.commonprefix([public_dir, templates_dir]), '.cache')
    if not os.path.exists(tmp_base):
        os.makedirs(tmp_base)
    if not os.path.isdir(os.path.dirname(templates_dir)):
        os.makedirs(os.path.dirname(templates_dir))
    tmp_dir = tempfile.mkdtemp(dir=tmp_base)
    #pylint: disable=too-many-nested-blocks
    try:
        for info in zip_file.infolist():
            if info.file_size == 0:
                # Crude way to detect directories
                continue
            tmp_path = None
            test_parts = os.path.normpath(info.filename).split(os.sep)[1:]
            if len(test_parts) > 0:
                base = test_parts.pop(0)
                if base == 'public':
                    if settings.PUBLIC_WHITELIST is not None:
                        if (os.path.join(*test_parts)
                            in settings.PUBLIC_WHITELIST):
                            tmp_path = safe_join(tmp_dir, base, *test_parts)
                    else:
                        tmp_path = safe_join(
                            tmp_dir, base, *test_parts)
                elif base == 'templates':
                    if settings.TEMPLATES_WHITELIST is not None:
                        if (os.path.join(*test_parts)
                            in settings.TEMPLATES_WHITELIST):
                            tmp_path = safe_join(tmp_dir, base, *test_parts)
                    else:
                        tmp_path = safe_join(tmp_dir, base, *test_parts)
                if tmp_path:
                    if not os.path.isdir(os.path.dirname(tmp_path)):
                        os.makedirs(os.path.dirname(tmp_path))
                    with open(tmp_path, 'wb') as extracted_file:
                        extracted_file.write(zip_file.read(info.filename))

        # Should be safe to move in-place at this point.
        # Templates are necessary while public resources (css, js)
        # are optional.
        tmp_public = safe_join(tmp_dir, 'public')
        tmp_templates = safe_join(tmp_dir, 'templates')
        mkdirs = []
        renames = []
        for paths in [(tmp_templates, templates_dir),
                     (tmp_public, public_dir)]:
            if os.path.exists(paths[0]):
                if not os.path.exists(os.path.dirname(paths[1])):
                    mkdirs += [os.path.exists(os.path.dirname(paths[1]))]
                renames += [paths]
        for path in mkdirs:
            os.makedirs(path)
        for paths in renames:
            if os.path.exists(paths[1]):
                LOGGER.info("remove previous path %s", paths[1])
                shutil.rmtree(paths[1])
            os.rename(paths[0], paths[1])
    finally:
        # Always delete the temporary directory, exception raised or not.
        shutil.rmtree(tmp_dir)

