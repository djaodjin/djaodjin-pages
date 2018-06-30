# Copyright (c) 2018, DjaoDjin inc.
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

from boto.exception import S3ResponseError
from django.core.files.storage import get_storage_class, FileSystemStorage
from django.http import Http404
from django.utils._os import safe_join
from django.utils import six
from rest_framework.generics import get_object_or_404

from . import settings
from .models import MediaTag, PageElement
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
                    try:
                        updated_at = storage.get_modified_time(media)
                    except AttributeError: # Django<2.0
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

    def get_default_storage(self, account=None, **kwargs):
        storage_class = get_storage_class()
        try:
            _ = storage_class.bucket_name
            storage_kwargs = {}
            storage_kwargs.update(**kwargs)
            for key in ['access_key', 'secret_key', 'security_token']:
                if key in self.request.session:
                    storage_kwargs[key] = self.request.session[key]
            return storage_class(
                bucket=get_bucket_name(account),
                location=get_media_prefix(account),
                **storage_kwargs)
        except AttributeError:
            LOGGER.debug("``%s`` does not contain a ``bucket_name``"\
                " field, default to FileSystemStorage.", storage_class)
        return self.get_file_system_storage(account)

    @staticmethod
    def get_file_system_storage(account=None):
        location = settings.MEDIA_ROOT
        base_url = settings.MEDIA_URL
        prefix = get_media_prefix(account)
        parts = location.split(os.sep)
        if prefix and prefix != parts[-1]:
            location = os.sep.join(parts[:-1] + [prefix, parts[-1]])
            if base_url.startswith('/'):
                base_url = base_url[1:]
            base_url = urljoin("/%s/" % prefix, base_url)
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
    media_prefix = settings.MEDIA_PREFIX
    if account:
        try:
            media_prefix = account.media_prefix
        except AttributeError:
            LOGGER.debug("``%s`` does not contain a ``media_prefix``"\
                " field.", account.__class__)
        if not media_prefix:
            media_prefix = str(account)
    return media_prefix


class ThemePackageMixin(AccountMixin):

    theme_url_kwarg = 'theme'

    @property
    def theme(self):
        return self.kwargs.get(self.theme_url_kwarg)

    @staticmethod
    def get_templates_dir(theme):
        if isinstance(settings.THEME_DIR_CALLABLE, six.string_types):
            from .compat import import_string
            settings.THEME_DIR_CALLABLE = import_string(
                settings.THEME_DIR_CALLABLE)
        theme_dir = settings.THEME_DIR_CALLABLE(theme)
        return safe_join(theme_dir, 'templates')

    @staticmethod
    def get_statics_dir(theme):
        return safe_join(settings.PUBLIC_ROOT, theme, 'static')
