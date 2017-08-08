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

import logging, os, shutil
from collections import OrderedDict
from functools import reduce #pylint:disable=redefined-builtin

from boto.s3.connection import S3Connection
from boto.exception import S3ResponseError
from django.core.files.storage import get_storage_class, FileSystemStorage
from django.http import Http404
from django.db.models import Q
from django.utils._os import safe_join
from django.utils import six
from rest_framework.generics import get_object_or_404

from . import settings
from .models import MediaTag, PageElement, ThemePackage
from .extras import AccountMixinBase

#pylint:disable=no-name-in-module,import-error
from django.utils.six.moves.urllib.parse import urljoin, urlsplit


LOGGER = logging.getLogger(__name__)


class AccountMixin(AccountMixinBase, settings.EXTRA_MIXIN):
    pass


class TrailMixin(object):
    """
    Generate a trail of PageElement based on a path.
    """

    @staticmethod
    def get_full_element_path(path):
        if not path:
            return []
        parts = path.split('/')
        if not parts[0]:
            parts.pop(0)
        results = []
        if parts:
            element = get_object_or_404(
                PageElement.objects.all(), slug=parts[-1])
            candidates = element.get_parent_paths(hints=parts[:-1])
            if not candidates:
                raise Http404("%s could not be found." % path)
            # XXX Implementation Note: if we have multiple candidates,
            # it means the hints were not enough to select a single path.
            # This is still OK to pick the first candidate as the breadcrumbs
            # should take a user back to the top-level page.
            if len(candidates) > 1:
                LOGGER.info("get_full_element_path has multiple candidates"\
                    " for '%s': %s", path, candidates)
            results = candidates[0]
        return results


class PageElementMixin(AccountMixin):

    lookup_field = 'slug'
    lookup_url_kwarg = 'slug'

    def get_queryset(self):
        return PageElement.objects.filter(account=self.account)


class UploadedImageMixin(object):

    def build_filter_list(self, validated_data):
        items = validated_data.get('items')
        filter_list = []
        if items:
            for item in items:
                location = item['location']
                parts = urlsplit(location)
                if parts.netloc == self.request.get_host():
                    location = parts.path
                filter_list += [location]
        return filter_list

    def list_media(self, storage, filter_list, prefix='.'):
        """
        Return a list of media from default storage
        """
        results = []
        total_count = 0
        if prefix.startswith('/'):
            prefix = prefix[1:]
        try:
            dirs, files = storage.listdir(prefix)
            for media in files:
                if prefix and prefix != '.':
                    media = prefix + '/' + media
                if not media.endswith('/') and media != "":
                    total_count += 1
                    location = storage.url(media)
                    updated_at = storage.modified_time(media)
                    normalized_location = location.split('?')[0]
                    if (filter_list is None
                        or normalized_location in filter_list):
                        results += [
                            {'location': location,
                            'tags': MediaTag.objects.filter(
                                location=normalized_location).values_list(
                                'tag', flat=True),
                            'updated_at': updated_at
                            }]
            for asset_dir in dirs:
                dir_results, dir_total_count = self.list_media(
                    storage, filter_list, prefix=prefix + '/' + asset_dir)
                results += dir_results
                total_count += dir_total_count
        except OSError:
            if storage.exists('.'):
                LOGGER.exception(
                    "Unable to list objects in %s.", storage.__class__.__name__)
        except S3ResponseError:
            LOGGER.exception(
                "Unable to list objects in %s bucket.", storage.bucket_name)

        # sort results by updated_at to sort by created_at.
        # Media are not updated, so updated_at = created_at
        return results, total_count

    def get_default_storage(self, account=None):
        storage_class = get_storage_class()
        try:
            _ = storage_class.bucket_name
            kwargs = {}
            for key in ['access_key', 'secret_key', 'security_token']:
                if key in self.request.session:
                    kwargs[key] = self.request.session[key]
            return storage_class(
                bucket=get_bucket_name(account),
                location=get_media_prefix(account),
                **kwargs)
        except AttributeError:
            LOGGER.debug("``%s`` does not contain a ``bucket_name``"\
                " field, default to FileSystemStorage.", storage_class)
        return self.get_file_system_storage(account)

    @staticmethod
    def get_file_system_storage(account=None):
        location = settings.MEDIA_ROOT
        base_url = settings.MEDIA_URL
        prefix = get_media_prefix(account)
        if prefix:
            location = os.path.join(location, prefix)
            base_url = urljoin(base_url, prefix)
        return FileSystemStorage(location=location, base_url=base_url)


def get_bucket_name(account=None):
    if account:
        for bucket_field in settings.BUCKET_NAME_FROM_FIELDS:
            try:
                bucket_name = getattr(account, bucket_field)
                if bucket_name:
                    return bucket_name
            except AttributeError:
                pass
    return settings.AWS_STORAGE_BUCKET_NAME


def get_media_prefix(account=None):
    if account:
        try:
            return account.media_prefix
        except AttributeError:
            LOGGER.debug("``%s`` does not contain a ``media_prefix``"\
                " field.", account.__class__)
    return settings.MEDIA_PREFIX


class ThemePackageMixin(AccountMixin):

    @staticmethod
    def get_templates_dir(theme):
        if isinstance(settings.THEME_DIR_CALLABLE, six.string_types):
            from ..compat import import_string
            settings.THEME_DIR_CALLABLE = import_string(
                settings.THEME_DIR_CALLABLE)
        theme_dir = settings.THEME_DIR_CALLABLE(theme.slug)
        return safe_join(theme_dir, 'templates')

    @staticmethod
    def get_statics_dir(theme):
        return safe_join(settings.PUBLIC_ROOT, theme.slug, 'static')

    @staticmethod
    def get_file_tree(root_path):
        tree = OrderedDict()
        root_path = root_path.rstrip(os.sep)
        start = root_path.rfind(os.sep) + 1
        for (dirpath, _, filenames) in os.walk(root_path):
            folders = dirpath[start:].split(os.sep)
            subdir = dict.fromkeys(filenames)
            parent = reduce(dict.get, folders[:-1], tree)
            parent[folders[-1]] = OrderedDict(subdir)
        return tree

    @staticmethod
    def find_file(root_path, file_path):
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

    @staticmethod
    def create_file(to_path):
        if not os.path.exists(os.path.dirname(to_path)):
            os.makedirs(os.path.dirname(to_path))
        if not os.path.exists(to_path):
            open(to_path, 'w').close()

    @staticmethod
    def copy_file(from_path, to_path):
        if not os.path.exists(os.path.dirname(to_path)):
            os.makedirs(os.path.dirname(to_path))
        if not os.path.exists(to_path):
            shutil.copyfile(
                from_path,
                to_path)

    def copy_files(self, from_dir, to_dir):
        for (dirpath, _, filenames) in os.walk(from_dir):
            for filename in filenames:
                from_path = os.path.join(dirpath, filename)
                to_path = os.path.join(
                    to_dir,
                    from_path.replace(os.path.join(from_dir, ''), ''))
                self.copy_file(
                    from_path,
                    to_path)

    @staticmethod
    def write_zipfile(zipf, dir_path, dir_option=""):
        for dirname, _, files in os.walk(dir_path):
            for filename in files:
                abs_file_path = os.path.join(
                    dirname, filename)
                rel_file_path = os.path.join(
                    dir_option,
                    abs_file_path.replace("%s/" % dir_path, ''))

                zipf.write(abs_file_path,
                    rel_file_path)
        return zipf
