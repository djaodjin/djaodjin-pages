# Copyright (c) 2015, Djaodjin Inc.
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

#pylint: disable=no-init,no-member,unused-variable
#pylint: disable=old-style-class,maybe-no-member

import json, hashlib, os

from django.core.cache import cache
from django.db.models import Q
from django.http import HttpResponse
from django.utils.encoding import force_text
from rest_framework import status
from rest_framework import generics
from rest_framework.parsers import FileUploadParser
from rest_framework.response import Response
from storages.backends.s3boto import S3BotoStorage

from .. import settings
from ..models import UploadedImage, PageElement
from ..serializers import UploadedImageSerializer
from ..mixins import AccountMixin, UploadedImageMixin
from ..tasks import S3UploadMediaTask


class MediaListAPIView(AccountMixin,
    UploadedImageMixin,
    generics.ListCreateAPIView):

    serializer_class = UploadedImageSerializer
    parser_classes = (FileUploadParser,)

    def post(self, request, *args, **kwargs):
        #pylint: disable=unused-argument,too-many-locals
        uploaded_file = request.FILES['file']
        sha1 = hashlib.sha1(uploaded_file.read()).hexdigest()

        # Store filenames with forward slashes, even on Windows
        file_name = force_text(uploaded_file.name.replace('\\', '/'))
        sha1_filename = sha1 + os.path.splitext(file_name)[1]
        sha1_path = os.path.join(settings.MEDIA_PATH, sha1_filename)
        # Replace filename by unique hash key
        uploaded_file.name = sha1_path
        account = self.get_account()
        bucket_name = self.get_bucket_name(account)
        storage = self.get_default_storage(account)
        storage_cache = self.get_cache_storage(account)
        result = {}
        if storage.exists(sha1_path) or storage_cache.exits(sha1_path):
            # File might be in the cache, yet to be uploaded to final storage.
            # File might be uploaded before database records are created.
            try:
                file_obj = UploadedImage.objects.get(
                    Q(uploaded_file=storage.url(sha1_path))
                    | Q(uploaded_file_cache=storage_cache.url(sha1_path)),
                    account=account)
                response_status = status.HTTP_200_OK
                result = {
                    "message": "%s is already in the gallery." % file_name}
            except UploadedImage.DoesNotExist:
                file_obj = UploadedImage.objects.create(
                    account=account,
                    uploaded_file=storage.url(sha1_path),
                    uploaded_file_cache=storage_cache.url(sha1_path),
                    file_name=file_name)
                response_status = status.HTTP_201_CREATED
        else:
            storage_cache.save(sha1_path, uploaded_file)
            if isinstance(storage, S3BotoStorage):
                file_obj = UploadedImage.objects.create(
                    account=account,
                    uploaded_file=None,
                    uploaded_file_cache=storage_cache.url(sha1_path),
                    file_name=file_name)
                upload_to_s3 = S3UploadMediaTask()
                upload_to_s3.delay(file_obj)
            else:
                file_obj = UploadedImage.objects.create(
                    account=account,
                    uploaded_file=storage.url(sha1_path),
                    uploaded_file_cache=storage_cache.url(sha1_path),
                    file_name=file_name)
            response_status = status.HTTP_201_CREATED
        serializer = UploadedImageSerializer(file_obj)
        result.update(serializer.data)
        return Response(result, status=response_status)

    def get_queryset(self):
        queryset = UploadedImage.objects.filter(
            account=self.get_account()).order_by("-created_at")
        search = self.request.GET.get('q')
        if search != '':
            queryset = queryset.filter(
                Q(tags__contains=search) | \
                Q(file_name__contains=search))\
                .order_by("-created_at")
        return queryset


class MediaUpdateDestroyAPIView(
    AccountMixin,
    UploadedImageMixin,
    generics.RetrieveUpdateDestroyAPIView):

    model = UploadedImage
    serializer_class = UploadedImageSerializer
    lookup_url_kwarg = 'slug'

    def get_queryset(self):
        return UploadedImage.objects.filter(
            account=self.get_account())

    def get_object(self):
        queryset = self.get_queryset()
        sha1 = self.kwargs.get(self.lookup_url_kwarg)
        instance = self.get_queryset().filter(
            Q(uploaded_file__contains=sha1)\
            |Q(uploaded_file_cache__contains=sha1))[0]
        return instance

    def delete(self, request, *args, **kwargs):
        file_obj = self.get_object()
        relative_path = file_obj.relative_path()
        storage = self.get_default_storage(file_obj.account)
        if storage.exists(relative_path):
            storage.delete(relative_path)
        cache_storage = self.get_cache_storage(file_obj.account)
        if cache_storage.exists(relative_path):
            cache_storage.delete(relative_path)

        page_elements = PageElement.objects.filter(
            text=file_obj.uploaded_file).delete()
        file_obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


def upload_progress(request, account_slug=None):
    #pylint: disable=unused-argument
    """
    Used by Ajax calls

    Return the upload progress and total length values
    """
    if 'X-Progress-ID' in request.GET:
        progress_id = request.GET['X-Progress-ID']
    elif 'X-Progress-ID' in request.META:
        progress_id = request.META['X-Progress-ID']
    if progress_id:
        cache_key = "%s_%s" % (request.META['REMOTE_ADDR'], progress_id)
        data = cache.get(cache_key)
        return HttpResponse(json.dumps(data))
