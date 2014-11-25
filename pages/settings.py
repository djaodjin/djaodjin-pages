# Copyright (c) 2014, DjaoDjin inc.
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
    'ACCOUNT_URL_KWARG': None,
    'MEDIA_PATH': 'pages/images/',
    'UPLOADED_TEMPLATE_DIR': None,
    'DISABLE_ACCOUNT_TEMPLATE_PATH': False,
    'UPLOADED_STATIC_DIR': None,
    'NO_LOCAL_STORAGE': False,
    'USE_S3': False,
    'S3_URL': None,
    'ENCRYPT_KEY': None,
    'FFMPEG_PATH': '/usr/local/bin/ffmpeg',

}

SLUG_RE = r'[a-zA-Z0-9_\-]+'

_SETTINGS.update(getattr(settings, 'PAGES', {}))

ACCOUNT_MODEL = _SETTINGS.get('ACCOUNT_MODEL')
ACCOUNT_URL_KWARG = _SETTINGS.get('ACCOUNT_URL_KWARG')
MEDIA_PATH = _SETTINGS.get('MEDIA_PATH')
UPLOADED_TEMPLATE_DIR = _SETTINGS.get('UPLOADED_TEMPLATE_DIR')
DISABLE_ACCOUNT_TEMPLATE_PATH = _SETTINGS.get('DISABLE_ACCOUNT_TEMPLATE_PATH')
UPLOADED_STATIC_DIR = _SETTINGS.get('UPLOADED_STATIC_DIR')
NO_LOCAL_STORAGE = _SETTINGS.get('NO_LOCAL_STORAGE')
USE_S3 = _SETTINGS.get('USE_S3')
S3_URL = _SETTINGS.get('S3_URL')
ENCRYPT_KEY = _SETTINGS.get('ENCRYPT_KEY')
FFMPEG_PATH = _SETTINGS.get('FFMPEG_PATH')
