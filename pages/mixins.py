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
from django.db.models import Q
from boto.s3.connection import S3Connection
from boto.exception import S3ResponseError

from . import settings
from .compat import import_string
from .models import MediaTag, PageElement, ThemePackage

LOGGER = logging.getLogger(__name__)


class AccountMixin(object):

    account_url_kwarg = settings.ACCOUNT_URL_KWARG

    @property
    def account(self):
        if not hasattr(self, '_account'):
            if settings.GET_CURRENT_ACCOUNT:
                self._account = import_string(settings.GET_CURRENT_ACCOUNT)()
            else:
                self._account = None
        return self._account


class UploadedImageMixin(object):

    @staticmethod
    def update_media_tag(tags, list_media):
        for item in list_media['results']:
            media_tags = MediaTag.objects.filter(location=item['location'])
            new_media_tags = []
            if tags:
                for tag in tags:
                    if tag != "":
                        new_media_tag, _ = MediaTag.objects.get_or_create(
                            tag=tag, location=item['location'])
                        new_media_tags += [new_media_tag]

            # compare new list and delete removed tags.
            for tag in media_tags:
                if not tag in new_media_tags:
                    tag.delete()

    @staticmethod
    def delete_media_items(storage, list_media):
        for item in list_media['results']:
            storage.delete(item['media'])

            # Delete all MediaTag and PageElement using this location
            MediaTag.objects.filter(location=item['location']).delete()
            PageElement.objects.filter(text=item['location']).delete()

    @staticmethod
    def build_filter_list(validated_data):
        items = validated_data.get('items')
        filter_list = []
        if items:
            for item in items:
                filter_list = item['location']
        return filter_list

    @staticmethod
    def list_media(storage, filter_list):
        """
        Return a list of media from default storage
        """
        results = []
        total = 0
        try:
            for media in storage.listdir('.')[1]:
                if not media.endswith('/') and media != "":
                    location = storage.url(media).split('?')[0]
                    total += 1
                    if not filter_list or location in filter_list:
                        results += [
                            {'location': location,
                            'tags': MediaTag.objects.filter(
                                location=location).values_list(
                                'tag', flat=True)
                            }]
        except OSError:
            LOGGER.exception(
                "Unable to list objects in %s.", storage.__class__.__name__)
        except S3ResponseError:
            LOGGER.exception(
                "Unable to list objects in %s bucket.", storage.bucket_name)
        return {'count': total, 'results': results}

    @staticmethod
    def list_delete_media(storage, filter_list):
        results = []
        total = 0
        try:
            for media in storage.listdir('.')[1]:
                if not media.endswith('/') and media != "":
                    location = storage.url(media).split('?')[0]
                    total += 1
                    if filter_list and location in filter_list:
                        results += [
                            {'location': location, 'media': media}]
        except OSError:
            LOGGER.exception(
                "Unable to list objects in %s.", storage.__class__.__name__)
        except S3ResponseError:
            LOGGER.exception(
                "Unable to list objects in %s bucket.", storage.bucket_name)
        return {'count': total, 'results': results}

    def get_default_storage(self, account=None):
        storage_class = get_storage_class()
        try:
            _ = storage_class.bucket_name
            return storage_class(
                bucket=get_bucket_name(account),
                location=get_media_prefix(account))
        except AttributeError:
            LOGGER.debug("``%s`` does not contain a ``bucket_name``"\
                " field, default to FileSystemStorage.", storage_class)
        return self.get_file_system_storage(account)

    @staticmethod
    def get_file_system_storage(account=None):
        location = settings.MEDIA_ROOT
        base_url = settings.MEDIA_URL
        bucket_name = get_bucket_name(account)
        if bucket_name:
            location = os.path.join(location, bucket_name)
            base_url = urljoin(base_url, bucket_name + '/')
        prefix = get_media_prefix(account)
        if prefix:
            location = os.path.join(location, prefix)
            base_url = urljoin(base_url, prefix)
        return FileSystemStorage(location=location, base_url=base_url)


def get_bucket_name(account=None):
    if not account:
        return settings.AWS_STORAGE_BUCKET_NAME
    try:
        bucket_name = account.bucket_name
    except AttributeError:
        LOGGER.debug("``%s`` does not contain a ``bucket_name``"\
            " field, using ``slug`` instead.", account.__class__)
        bucket_name = None
    if not bucket_name:
        # We always need a non-empty bucket_name in order
        # to partition the namespace.
        bucket_name = account.slug
    return bucket_name

def get_media_prefix(account=None):
    if not account:
        return settings.MEDIA_PREFIX
    try:
        return account.media_prefix
    except AttributeError:
        LOGGER.debug("``%s`` does not contain a ``media_prefix``"\
            " field.", account.__class__)
    return ""


class ThemePackageMixin(AccountMixin):

    @staticmethod
    def get_file_tree(root_path):
        tree = {}
        root_path = root_path.rstrip(os.sep)
        start = root_path.rfind(os.sep) + 1
        for (dirpath, _, filenames) in os.walk(root_path):
            folders = dirpath[start:].split(os.sep)
            subdir = dict.fromkeys(filenames)
            parent = reduce(dict.get, folders[:-1], tree)
            parent[folders[-1]] = subdir
        return tree

    @staticmethod
    def get_file_path(root_path, file_path):
        abs_file_path = None
        for (dirpath, _, filenames) in os.walk(root_path):
            for filename in filenames:
                if file_path in os.path.join(dirpath, filename):
                    abs_file_path = os.path.join(dirpath, filename)
        return abs_file_path

    def get_queryset(self):
        queryset = ThemePackage.objects.filter(
            Q(account=self.account)|Q(account=None)).order_by('-created_at')
        return queryset

    @staticmethod
    def get_file_from_s3(bucket, orig, dest):
        conn = S3Connection()
        bucket = conn.get_bucket(bucket)
        key = bucket.get_key(orig)

        if not key:
            return None
        else:# Save file from S3 into tmp_dir
            key.get_contents_to_filename(dest)
            return dest
