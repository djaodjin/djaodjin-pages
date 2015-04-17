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

from django.http import HttpResponse
from django.core.cache import cache
from django.utils.text import slugify
from django.core.files.storage import get_storage_class

from django.db.models import Q

from storages.backends.s3boto import S3BotoStorage

from rest_framework import status
from rest_framework import generics
from rest_framework.parsers import FileUploadParser
from rest_framework.response import Response

from pages.settings import MEDIA_ROOT
from pages.models import UploadedImage, PageElement
from pages.serializers import UploadedImageSerializer
from pages.mixins import AccountMixin, UploadedImageMixin
from pages.tasks import upload_to_s3


class MediaListAPIView(AccountMixin,
    UploadedImageMixin,
    generics.ListCreateAPIView):

    serializer_class = UploadedImageSerializer
    parser_classes = (FileUploadParser,)

    def post(self, request,
        account_slug=None, format=None, *args, **kwargs):#pylint: disable=unused-argument,redefined-builtin, too-many-locals

        uploaded_file = request.FILES['file']
        existing_file = False
        file_name = slugify(uploaded_file.name)
        sha1_filename = hashlib.sha1(uploaded_file.read()).hexdigest() + '.' +\
            str(uploaded_file).split('.')[1].lower()

        # Replace filename by unique hash key
        uploaded_file.name = sha1_filename
        account = self.get_account()

        if get_storage_class() == S3BotoStorage:
            file_obj = UploadedImage.objects.create(
                uploaded_file_cache=uploaded_file,
                account=self.get_account(),
                file_name=file_name)
            upload_to_s3.delay(file_obj, uploaded_file)
        else:
            file_obj = UploadedImage.objects.create(
                uploaded_file=uploaded_file,
                account=self.get_account(),
                file_name=file_name)

        serializer = UploadedImageSerializer(file_obj)

        file_src = serializer.data['file_src']
        if not file_src:
            file_src = serializer.data['file_src_cache']
        response = {
                'uploaded_file': file_src,
                'exist': existing_file,
                'unique_id':serializer.data['unique_id']
                }
        return Response(response, status=status.HTTP_200_OK)

    def get_queryset(self):
        queryset = UploadedImage.objects.filter(
            account=self.get_account()).order_by("-created_at")
        if self.request.GET.get('q') != '':
            queryset = queryset.filter(
                Q(tags__contains=self.request.GET.get('q')) | \
                Q(file_name__contains=self.request.GET.get('q')))\
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
        unique_id = self.kwargs.get(self.lookup_url_kwarg)
        instance = self.get_queryset().filter(
            Q(uploaded_file__contains=unique_id)\
            |Q(uploaded_file_cache__contains=unique_id))[0]
        return instance

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        storage_backend = self.get_default_storage(instance)
        if storage_backend:
            try:
                storage_backend.delete(instance.uploaded_file.name)
            except ValueError:
                # No file found on S3 delete cache file
                os.remove(os.path.join(
                    MEDIA_ROOT, instance.uploaded_file_cache.name))
        else:
            os.remove(os.path.join(MEDIA_ROOT, instance.uploaded_file.name))
        instance.delete()
        page_elements = PageElement.objects.filter(text=instance.uploaded_file.url.split('?')[0])
        for page_element in page_elements:
            page_elements.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


def upload_progress(request, account_slug=None):#pylint: disable=unused-argument
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
