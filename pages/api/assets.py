# Copyright (c) 2024, Djaodjin Inc.
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


import hashlib, logging, os

import boto3
from deployutils.helpers import datetime_or_now
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponseRedirect
from django.utils.module_loading import import_string
from rest_framework import parsers, status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response as HttpResponse

from .. import settings
from ..compat import (NoReverseMatch, force_str, gettext_lazy as _, reverse,
    urljoin, urlparse, get_storage_class)
from ..mixins import AccountMixin
from ..serializers import AssetSerializer


LOGGER = logging.getLogger(__name__)

URL_PATH_SEP = '/'


class AssetAPIView(AccountMixin, GenericAPIView):

    store_hash = True
    replace_stored = False
    content_type = None
    serializer_class = AssetSerializer

    @staticmethod
    def as_signed_url(location, request):
        parts = urlparse(location)
        key_name = parts.path.lstrip('/')
            # we remove leading '/' otherwise S3 copy triggers a 404
            # because it creates an URL with '//'.
        storage = get_default_storage(request)
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
        location = self.as_signed_url(kwargs.get('path'), request)
        http_accepts = [item.strip()
            for item in request.META.get('HTTP_ACCEPT', '*/*').split(',')]
        if 'text/html' in http_accepts:
            return HttpResponseRedirect(location)
        return HttpResponse(self.get_serializer().to_representation({
            'location': location}))

    def delete(self, request, *args, **kwargs):
        """
        Deletes static assets file

        **Examples

        .. code-block:: http

            DELETE /api/supplier-1/assets/supporting-evidence.pdf HTTP/1.1

        """
        #pylint: disable=unused-variable,unused-argument,too-many-locals
        storage = get_default_storage(self.request)
        storage.delete(kwargs.get('path'))
        return HttpResponse({
            'detail': _('Media correctly deleted.')},
            status=status.HTTP_200_OK)


class UploadAssetAPIView(AccountMixin, GenericAPIView):

    store_hash = True
    replace_stored = False
    content_type = None
    serializer_class = AssetSerializer
    parser_classes = (parsers.JSONParser, parsers.FormParser,
        parsers.MultiPartParser, parsers.FileUploadParser)

    def post(self, request, *args, **kwargs):
        """
        Uploads a static asset file

        **Examples

        .. code-block:: http

            POST /api/supplier-1/assets HTTP/1.1

        responds

        .. code-block:: json

            {
              "location": "/media/image-001.jpg",
              "updated_at": "2016-10-26T00:00:00.00000+00:00"
            }
        """
        is_public_asset = request.query_params.get('public', False)
        location = request.data.get('location', None)
        response_data, response_status = process_upload(
            request, self.account, location, is_public_asset,
            self.store_hash, self.replace_stored, self.content_type)
        return HttpResponse(
            AssetSerializer().to_representation(response_data),
            status=response_status)


def process_upload(request, account=None, location=None, is_public_asset=None,
                   store_hash=None, replace_stored=None, content_type=None):
    #pylint:disable=too-many-arguments,too-many-locals
    media_prefix = _get_media_prefix()
    response_status = status.HTTP_200_OK

    if location:
        parts = urlparse(location)
        bucket_name = parts.netloc.split('.')[0]
        src_key_name = parts.path.lstrip(URL_PATH_SEP)
        # we remove leading '/' otherwise S3 copy triggers a 404
        # because it creates an URL with '//'.
        prefix = os.path.dirname(src_key_name)
        if prefix:
            prefix += URL_PATH_SEP
        ext = os.path.splitext(src_key_name)[1]

        s3_client = boto3.client('s3')
        data = s3_client.get_object(Bucket=bucket_name, Key=src_key_name)
        uploaded_file = data['Body']
        if prefix.startswith(media_prefix):
            prefix = prefix[len(media_prefix) + 1:]
        storage_key_name = "%s%s%s" % (prefix,
            hashlib.sha256(uploaded_file.read()).hexdigest(), ext)

        dst_key_name = "%s/%s" % (media_prefix, storage_key_name)
        LOGGER.info("S3 bucket %s: copy %s to %s",
                    bucket_name, src_key_name, dst_key_name)
        storage = get_default_storage(request)
        if is_public_asset:
            extra_args = {'ACL': "public-read"}
        else:
            extra_args = {
                'ServerSideEncryption': settings.AWS_SERVER_SIDE_ENCRYPTION}
        if ext in ['.pdf']:
            extra_args.update({'ContentType': 'application/pdf'})
        elif ext in ['.jpg']:
            extra_args.update({'ContentType': 'image/jpeg'})
        elif ext in ['.png']:
            extra_args.update({'ContentType': 'image/png'})
        s3_client.copy({'Bucket': bucket_name, 'Key': src_key_name},
                       bucket_name, dst_key_name, ExtraArgs=extra_args)
        # XXX still can't figure out why we get a permission denied on DeleteObject.
        #            s3_client.delete_object(Bucket=bucket_name, Key=src_key_name)
        location = storage.url(storage_key_name)

    elif 'file' in request.data:
        uploaded_file = request.data['file']
        if content_type:
            # We optionally force the content_type because S3Store uses
            # mimetypes.guess and surprisingly it doesn't get it correct
            # for 'text/css'.
            uploaded_file.content_type = content_type
        sha1 = hashlib.sha1(uploaded_file.read()).hexdigest()

        # Store filenames with forward slashes, even on Windows
        filename = force_str(uploaded_file.name.replace('\\', '/'))
        sha1_filename = sha1 + os.path.splitext(filename)[1]
        storage = get_default_storage(request)
        stored_filename = sha1_filename if store_hash else filename
        if not is_public_asset:
            stored_filename = '/'.join(
                [str(account), stored_filename])

        LOGGER.debug("upload %s to %s", filename, stored_filename)
        if storage.exists(stored_filename) and replace_stored:
            storage.delete(stored_filename)
        storage.save(stored_filename, uploaded_file)
        response_status = status.HTTP_201_CREATED
        location = storage.url(stored_filename)

    else:
        raise ValidationError({'detail':
           _("Either 'location' or 'file' must be specified.")})

    if not is_public_asset:
        path = urlparse(location).path.lstrip(URL_PATH_SEP)
        if path.startswith(media_prefix):
            path = path[len(media_prefix):].lstrip(URL_PATH_SEP)
        try:
            location = request.build_absolute_uri(
                reverse('pages_api_asset', args=(account, path,)))
        except NoReverseMatch:
            location = request.build_absolute_uri(
                reverse('pages_api_asset', args=(path,)))

    return ({
        'location': location,
        'updated_at': datetime_or_now()},
        response_status)


def get_default_storage(request, **kwargs):
    """
    Returns the default storage for an account.
    """
    if settings.DEFAULT_STORAGE_CALLABLE:
        storage = import_string(settings.DEFAULT_STORAGE_CALLABLE)(
            request, **kwargs)
        return storage
    return get_default_storage_base(request, **kwargs)


def get_default_storage_base(request, public=False, **kwargs):
    # default implementation
    storage_class = get_storage_class()
    if storage_class.__name__.endswith('3Storage'):
        # Hacky way to test for `storages.backends.s3.S3Storage`
        # and `storages.backends.s3boto3.S3Boto3Storage` without importing
        # the optional package 'django-storages'.
        storage_kwargs = {}
        storage_kwargs.update(**kwargs)
        if public:
            storage_kwargs.update({'default_acl': 'public-read'})
        bucket_name = _get_bucket_name()
        location = _get_media_prefix()
        LOGGER.debug("create %s(bucket_name='%s', location='%s', %s)",
            storage_class.__name__, bucket_name, location, storage_kwargs)
        storage = storage_class(bucket_name=bucket_name, location=location,
            **storage_kwargs)
        for key in ['access_key', 'secret_key', 'security_token']:
            if key in request.session:
                setattr(storage, key, request.session[key])
        return storage
    LOGGER.debug("``%s`` does not contain a ``bucket_name``"\
        " field, default to FileSystemStorage.", storage_class)
    return _get_file_system_storage()


def _get_bucket_name():
    return settings.AWS_STORAGE_BUCKET_NAME


def _get_file_system_storage():
    location = settings.MEDIA_ROOT
    base_url = settings.MEDIA_URL
    prefix = _get_media_prefix()
    parts = location.split(os.sep)
    if prefix and prefix != parts[-1]:
        location = os.sep.join(parts[:-1] + [prefix, parts[-1]])
        if base_url.startswith('/'):
            base_url = base_url[1:]
        base_url = urljoin("/%s/" % prefix, base_url)
    return FileSystemStorage(location=location, base_url=base_url)


def _get_media_prefix():
    return settings.MEDIA_PREFIX
