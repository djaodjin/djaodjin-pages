# Copyright (c) 2016, DjaoDjin inc.
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

import os

from django.conf import settings

def theme_dir(account): #pylint:disable=unused-argument
    return os.path.join(settings.BASE_DIR, 'themes')

_SETTINGS = {
    'ACCOUNT_MODEL': getattr(settings, 'AUTH_USER_MODEL', None),
    'ACCOUNT_URL_KWARG': None,
    'ACTIVE_THEME_CALLABLE': None,
    'DEFAULT_ACCOUNT_CALLABLE': '',
    'DEFAULT_ACCOUNT_ID': getattr(settings, 'SITE_ID', 1),
    'EXTRA_MIXIN': object,
    'MEDIA_PREFIX': '',
    'MEDIA_URL': getattr(settings, 'MEDIA_URL'),
    'MEDIA_ROOT': getattr(settings, 'MEDIA_ROOT'),
    'AWS_STORAGE_BUCKET_NAME': getattr(
        settings, 'AWS_STORAGE_BUCKET_NAME', None),
    'PUBLIC_ROOT': getattr(settings, 'STATIC_ROOT'),
    'PUBLIC_WHITELIST': None,
    'TEMPLATES_BLACKLIST': [],
    'TEMPLATES_WHITELIST': None,
    'THEME_DIR_CALLABLE': theme_dir,
}

_SETTINGS.update(getattr(settings, 'PAGES', {}))

ACCOUNT_MODEL = _SETTINGS.get('ACCOUNT_MODEL')
ACCOUNT_URL_KWARG = _SETTINGS.get('ACCOUNT_URL_KWARG')
DEFAULT_ACCOUNT_CALLABLE = _SETTINGS.get('DEFAULT_ACCOUNT_CALLABLE')
DEFAULT_ACCOUNT_ID = _SETTINGS.get('DEFAULT_ACCOUNT_ID')
EXTRA_MIXIN = _SETTINGS.get('EXTRA_MIXIN')
MEDIA_PREFIX = _SETTINGS.get('MEDIA_PREFIX')
MEDIA_URL = _SETTINGS.get('MEDIA_URL')
MEDIA_ROOT = _SETTINGS.get('MEDIA_ROOT')
AWS_STORAGE_BUCKET_NAME = _SETTINGS.get('AWS_STORAGE_BUCKET_NAME')
PUBLIC_ROOT = _SETTINGS.get('PUBLIC_ROOT')
PUBLIC_WHITELIST = _SETTINGS.get('PUBLIC_WHITELIST')
TEMPLATES_BLACKLIST = _SETTINGS.get('TEMPLATES_BLACKLIST')
TEMPLATES_WHITELIST = _SETTINGS.get('TEMPLATES_WHITELIST')
ACTIVE_THEME_CALLABLE = _SETTINGS.get('ACTIVE_THEME_CALLABLE')
THEME_DIR_CALLABLE = _SETTINGS.get('THEME_DIR_CALLABLE')

SLUG_RE = r'[a-zA-Z0-9_\-]+'

# Sanitizer settings
ALLOWED_TAGS = [
    'a',
    'span',
    'h1',
    'h2',
    'h3',
    'b',
    'pre',
    'em',
    'li',
    'ol',
    'strong',
    'ul',
    'i',
    'div',
    'br',
    'p',
    'img'
]

ALLOWED_ATTRIBUTES = {
    '*': ['style'],
    'a': ['href', 'title'],
    'img': ['src', 'title', 'style']
}

ALLOWED_STYLES = ['text-align', 'max-width', 'line-height']
