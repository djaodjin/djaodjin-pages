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

import os

from django.conf import settings

_SETTINGS = {
    'ACCOUNT_LOOKUP_FIELD': 'username',
    'ACCOUNT_MODEL': getattr(settings, 'AUTH_USER_MODEL', None),
    'ACCOUNT_URL_KWARG': None,
    'APP_NAME': getattr(settings, 'APP_NAME',
        os.path.basename(settings.BASE_DIR)),
    'AUTH_USER_MODEL': getattr(settings, 'AUTH_USER_MODEL', None),
    'AWS_SERVER_SIDE_ENCRYPTION': "AES256",
    'AWS_STORAGE_BUCKET_NAME':
        getattr(settings, 'AWS_STORAGE_BUCKET_NAME',
            getattr(settings, 'APP_NAME',
                None)),
    'BUCKET_NAME_FROM_FIELDS': ['bucket_name'],
    'COMMENT_MAX_LENGTH': getattr(settings, 'COMMENT_MAX_LENGTH', 3000),
    'DEFAULT_ACCOUNT_CALLABLE': '',
    'DEFAULT_STORAGE_CALLABLE': '',
    'EXTRA_FIELD': None,
    'MEDIA_PREFIX': ""
}

_SETTINGS.update(getattr(settings, 'PAGES', {}))

ACCOUNT_LOOKUP_FIELD = _SETTINGS.get('ACCOUNT_LOOKUP_FIELD')
ACCOUNT_MODEL = _SETTINGS.get('ACCOUNT_MODEL')
ACCOUNT_URL_KWARG = _SETTINGS.get('ACCOUNT_URL_KWARG')
APP_NAME = _SETTINGS.get('APP_NAME')
AUTH_USER_MODEL = _SETTINGS.get('AUTH_USER_MODEL')
AWS_SERVER_SIDE_ENCRYPTION = _SETTINGS.get('AWS_SERVER_SIDE_ENCRYPTION')
AWS_STORAGE_BUCKET_NAME = _SETTINGS.get('AWS_STORAGE_BUCKET_NAME')
BUCKET_NAME_FROM_FIELDS = _SETTINGS.get('BUCKET_NAME_FROM_FIELDS')
COMMENT_MAX_LENGTH = _SETTINGS.get('COMMENT_MAX_LENGTH')
DEFAULT_ACCOUNT_CALLABLE = _SETTINGS.get('DEFAULT_ACCOUNT_CALLABLE')
DEFAULT_STORAGE_CALLABLE = _SETTINGS.get('DEFAULT_STORAGE_CALLABLE')
EXTRA_FIELD = _SETTINGS.get('EXTRA_FIELD')
MEDIA_PREFIX = _SETTINGS.get('MEDIA_PREFIX')

LANGUAGE_CODE = getattr(settings, 'LANGUAGE_CODE')
SLUG_RE = r'[a-zA-Z0-9_\-\+\.]+'
PATH_RE = r'([a-zA-Z0-9\-]+/)*[a-zA-Z0-9\-]*'
NON_EMPTY_PATH_RE = r'([a-zA-Z0-9\-]+/)*[a-zA-Z0-9\-]+'

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
