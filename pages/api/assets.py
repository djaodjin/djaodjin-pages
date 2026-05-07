# Copyright (c) 2026, Djaodjin Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


import logging

from django.http import HttpResponseRedirect
from rest_framework import status
from rest_framework.generics import RetrieveUpdateDestroyAPIView
from rest_framework.response import Response as HttpResponse
from extended_templates.api.assets import (
    ListUploadAssetAPIView as ListUploadAssetBaseAPIView,
    resolve_permanent_location)
from extended_templates.api.serializers import AssetSerializer
from extended_templates.models import MediaTag
from extended_templates.utils import _get_media_prefix, get_default_storage

from ..compat import (NoReverseMatch,
    gettext_lazy as _, reverse, urlparse, urlunparse)
from ..mixins import AccountMixin


LOGGER = logging.getLogger(__name__)

URL_PATH_SEP = '/'


class AssetAPIView(AccountMixin, RetrieveUpdateDestroyAPIView):

    serializer_class = AssetSerializer

    def as_signed_url(self, key_name, request):
        storage = get_default_storage(request, self.account)
        return storage.url(key_name)


    def get(self, request, *args, **kwargs):
        """
        Expiring link to download asset file

        **Examples

        .. code-block:: http

            GET /api/supplier-1/assets/supporting-evidence.pdf HTTP/1.1

        responds

        .. code-block:: json

            {
              "location": "https://example-bucket.s3.amazon.com\
/supporting-evidence.pdf",
              "updated_at": "2016-10-26T00:00:00.00000+00:00"
            }
        """
        #pylint:disable=unused-argument
        storage = get_default_storage(request, self.account)
        key_name = kwargs.get('path')
        parts = urlparse(storage.url(''))
        base_storage_pat = urlunparse(
            (parts.scheme, parts.netloc, parts.path, None, None, None))

        # convert `/api/{profile}/assets/{path}` to a URL on S3.
        permanent_location = resolve_permanent_location(key_name, storage)
        if permanent_location.startswith(base_storage_pat):
            key_name = permanent_location[len(base_storage_pat):]

        location = self.as_signed_url(key_name, request)
        http_accepts = [item.strip()
            for item in request.META.get('HTTP_ACCEPT', '*/*').split(',')]
        if 'text/html' in http_accepts:
            return HttpResponseRedirect(location)

        updated_at = storage.get_modified_time(key_name)
        media_tags = MediaTag.objects.filter(location=permanent_location)
        return HttpResponse(self.get_serializer().to_representation({
            'location': location,
            'updated_at': updated_at,
            'tags': media_tags.values_list('tag', flat=True)
        }))

    def delete(self, request, *args, **kwargs):
        """
        Deletes static assets file

        **Examples

        .. code-block:: http

            DELETE /api/supplier-1/assets/supporting-evidence.pdf HTTP/1.1

        """
        #pylint: disable=unused-variable,unused-argument,too-many-locals
        storage = get_default_storage(request, self.account)
        key_name = kwargs.get('path')
        parts = urlparse(storage.url(''))
        base_storage_pat = urlunparse(
            (parts.scheme, parts.netloc, parts.path, None, None, None))

        # convert `/api/{profile}/assets/{path}` to a URL on S3.
        permanent_location = resolve_permanent_location(key_name, storage)
        if permanent_location.startswith(base_storage_pat):
            key_name = permanent_location[len(base_storage_pat):]
            storage.delete(key_name)
        MediaTag.objects.filter(location=permanent_location).delete()
        return HttpResponse({
            'detail': _('Media correctly deleted.')},
            status=status.HTTP_200_OK)


class ListUploadAssetAPIView(AccountMixin, ListUploadAssetBaseAPIView):
    """
    Lists uploaded static asset files

    **Examples

    .. code-block:: http

        GET /api/supplier-1/assets HTTP/1.1

    responds

    .. code-block:: json

        {
          "count": 1,
          "previous": null,
          "next": null,
          "results": [{
              "location": "https://example-bucket.s3.amazon.com\
/supporting-evidence.pdf",
              "updated_at": "2016-10-26T00:00:00.00000+00:00",
              "tags": []
          }]
        }
    """
    is_public_asset = False

    def resolve_asset_location(self, location):
        if not self.is_public_asset:
            media_prefix = _get_media_prefix()
            path = urlparse(location).path.lstrip(URL_PATH_SEP)
            if path:
                if path.startswith(media_prefix):
                    path = path[len(media_prefix):].lstrip(URL_PATH_SEP)
            else:
                # We cannot use an empty path in the `reverse` calls,
                # so we use a '/' that will then be removed (i.e.
                # `.rstrip(URL_PATH_SEP)`).
                path = URL_PATH_SEP
            try:
                location = self.request.build_absolute_uri(
                    reverse('pages_api_asset', args=(self.account, path,)))
            except NoReverseMatch:
                location = self.request.build_absolute_uri(
                    reverse('pages_api_asset', args=(path,)))
            location = location.rstrip(URL_PATH_SEP)
        return location.rstrip()
