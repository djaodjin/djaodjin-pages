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

ACCOUNT_MODEL = getattr(settings,
    'PAGES_ACCOUNT_MODEL', settings.AUTH_USER_MODEL)

ACCOUNT_URL_KWARG = getattr(settings,
    'PAGES_ACCOUNT_URL_KWARG', None)

SLUG_RE = r'[a-zA-Z0-9_\-]+'

MEDIA_PATH = getattr(settings,
    'PAGES_MEDIA_PATH', 'pages/images/')

UPLOADED_TEMPLATE_DIR = getattr(settings,
    'PAGES_UPLOADED_TEMPLATE_DIR', None)

UPLOADED_STATIC_DIR = getattr(settings,
    'PAGES_UPLOADED_STATIC_DIR', None)


# If False upload only to S3.
NO_LOCAL_STORAGE = getattr(settings,
    'PAGES_NO_LOCAL_STORAGE', False)

USE_S3 = getattr(settings, 'USE_S3', False)

S3_URL = getattr(settings, 'S3_URL', None)

ENCRYPT_KEY = getattr(settings, 'PAGES_ENCRYPT_KEY', None)

FFMPEG_PATH = getattr(settings, 'PAGES_FFMPEG_PATH', '/usr/local/bin/ffmpeg')
