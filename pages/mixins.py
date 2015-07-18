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

import logging, os

from django.core.files.storage import get_storage_class, FileSystemStorage
#pylint:disable=no-name-in-module,import-error
from django.utils.six.moves.urllib.parse import urljoin

from . import settings
from .compat import import_string

LOGGER = logging.getLogger(__name__)


class AccountMixin(object):

    account_url_kwarg = settings.ACCOUNT_URL_KWARG

    @staticmethod
    def get_account():
        if settings.GET_CURRENT_ACCOUNT:
            return import_string(settings.GET_CURRENT_ACCOUNT)()
        return None


class UploadedImageMixin(object):

    def get_media(self, storage, filter_list):
        list_media = self.list_media(storage, filter_list)
        if len(list_media) == 1:
            return list_media[0]
        return None

    @staticmethod
    def list_media(storage, filter_list):
        list_media = []
        if storage.exists(''):
            for media in storage.listdir('')[1]:
                if not media.endswith('/') and media != "":
                    media_url = storage.url(media).split('?')[0]
                    if not filter_list or media_url in filter_list:
                        sha1 = os.path.splitext(os.path.basename(media_url))[0]
                        list_media += [
                            {'file_src': media_url,
                            'sha1': sha1,
                            'media': media}]
        return list_media

    @staticmethod
    def get_bucket_name(account=None):
        if account:
            try:
                bucket_name = account.bucket_name
            except AttributeError:
                LOGGER.warning("``%s`` does not contain a ``bucket_name``"\
" field, using ``slug`` instead.", account.__class__)
                bucket_name = account.slug
        else:
            bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        return bucket_name

    @staticmethod
    def get_media_prefix(account=None):
        if account:
            try:
                return account.media_prefix
            except AttributeError:
                LOGGER.warning("``%s`` does not contain a ``media_prefix``"\
" field.", account.__class__)
        return settings.MEDIA_PREFIX

    def get_default_storage(self, account=None):
        if get_storage_class() != FileSystemStorage:
            return get_storage_class()(
                bucket=self.get_bucket_name(account),
                location=self.get_media_prefix(account))
        return self.get_cache_storage(account)

    def get_cache_storage(self, account=None):
        bucket_name = self.get_bucket_name(account)
        prefix = self.get_media_prefix(account)
        return FileSystemStorage(
            location=os.path.join(settings.MEDIA_ROOT, bucket_name, prefix),
            base_url=urljoin(settings.MEDIA_URL, bucket_name + '/', prefix))
