# Copyright (c) 2015, DjaoDjin inc.
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

from django.conf import settings as django_settings

try:
    from django.contrib.auth import get_user_model
except ImportError: # django < 1.5
    from django.contrib.auth.models import User #pylint: disable=unused-import
else:
    User = get_user_model()                     #pylint: disable=invalid-name


try:
    #pylint: disable=no-name-in-module, unused-import
    from django.utils.module_loading import import_string
except ImportError: # django < 1.7
    #pylint: disable=unused-import
    from django.utils.module_loading import import_by_path as import_string


try:
    #pylint: disable=no-name-in-module, unused-import
    from django.template.context_processors import csrf
except ImportError: # django < 1.8
    from django.core.context_processors import csrf #pylint: disable=unused-import

try:
    #pylint: disable=no-name-in-module, unused-import
    from django.template.exceptions import TemplateDoesNotExist
except ImportError:
    from django.template.base import TemplateDoesNotExist #pylint: disable=unused-import


def get_loaders():
    loaders = []
    try:
        from django.template.loader import _engine_list #pylint: disable=no-name-in-module
        engines = _engine_list()
        for engine in engines:
            try:
                loaders += engine.engine.template_loaders
            except AttributeError:
                pass
            try:
                loaders += engine.template_loaders
            except AttributeError:
                pass

    except ImportError:# django < 1.8
        from django.template.loader import find_template_loader
        for loader_name in django_settings.TEMPLATE_LOADERS:
            template_loader = find_template_loader(loader_name)
            if template_loader is not None:
                loaders.append(template_loader)
    return loaders
