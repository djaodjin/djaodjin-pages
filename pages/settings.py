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

from django.conf import settings


_SETTINGS = {
    'ACCOUNT_MODEL': settings.AUTH_USER_MODEL,
    'GET_CURRENT_ACCOUNT': '',
    'ACCOUNT_URL_KWARG': None,
    'MEDIA_PREFIX': '',
    'MEDIA_URL': getattr(settings, 'MEDIA_URL'),
    'MEDIA_ROOT': getattr(settings, 'MEDIA_ROOT'),
    'AWS_STORAGE_BUCKET_NAME': getattr(
        settings, 'AWS_STORAGE_BUCKET_NAME', None),
    'PUBLIC_ROOT': getattr(settings, 'STATIC_ROOT'),
    'PUBLIC_WHITELIST': None,
    'TEMPLATES_ROOT': getattr(settings, 'TEMPLATE_DIRS')[0],
    'TEMPLATES_WHITELIST': None
}

SLUG_RE = r'[a-zA-Z0-9_\-]+'

_SETTINGS.update(getattr(settings, 'PAGES', {}))

ACCOUNT_MODEL = _SETTINGS.get('ACCOUNT_MODEL')
GET_CURRENT_ACCOUNT = _SETTINGS.get('GET_CURRENT_ACCOUNT')
ACCOUNT_URL_KWARG = _SETTINGS.get('ACCOUNT_URL_KWARG')
MEDIA_PREFIX = _SETTINGS.get('MEDIA_PREFIX')
MEDIA_URL = _SETTINGS.get('MEDIA_URL')
MEDIA_ROOT = _SETTINGS.get('MEDIA_ROOT')
AWS_STORAGE_BUCKET_NAME = _SETTINGS.get('AWS_STORAGE_BUCKET_NAME')
PUBLIC_ROOT = _SETTINGS.get('PUBLIC_ROOT')
TEMPLATES_ROOT = _SETTINGS.get('TEMPLATES_ROOT')
PUBLIC_WHITELIST = _SETTINGS.get('PUBLIC_WHITELIST')
TEMPLATES_WHITELIST = _SETTINGS.get('TEMPLATES_WHITELIST')
