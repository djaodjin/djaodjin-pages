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
from django.db.models import Q
from django.core.files.storage import FileSystemStorage

from storages.backends.s3boto import S3BotoStorage

from rest_framework import status
from rest_framework import generics
from rest_framework.parsers import FileUploadParser
from rest_framework.response import Response

from pages import settings
from pages.models import UploadedImage, PageElement
from pages.serializers import UploadedImageSerializer
from pages.mixins import AccountMixin, UploadedImageMixin
from pages.tasks import S3UploadMediaTask


class MediaListAPIView(AccountMixin,
    UploadedImageMixin,
    generics.ListCreateAPIView):

    serializer_class = UploadedImageSerializer
    parser_classes = (FileUploadParser,)

    def post(self, request, *args, **kwargs):#pylint: disable=unused-argument, too-many-locals
        uploaded_file = request.FILES['file']
        existing_file = False
        file_name = uploaded_file.name
        sha1_filename = hashlib.sha1(uploaded_file.read()).hexdigest() + '.' +\
            str(uploaded_file).split('.')[1].lower()

        # Replace filename by unique hash key
        uploaded_file.name = sha1_filename
        account = self.get_account()
        storage = storage = self.get_default_storage(account)

        # If account and local storage add account.slug in path
        if account and not isinstance(storage, S3BotoStorage):
            media_path = os.path.join(settings.MEDIA_PATH, account.slug)
        else:
            media_path = settings.MEDIA_PATH

        if storage.exists(os.path.join(media_path, sha1_filename)):

            file_obj = UploadedImage.objects.get(
                Q(file_path=os.path.join(media_path, sha1_filename))|
                Q(file_path=os.path.join(media_path, sha1_filename)),
                account=account)

            serializer = UploadedImageSerializer(file_obj)
            return Response({'message':"Image already in your gallery."},
                status=status.HTTP_400_BAD_REQUEST)

        else:
            if isinstance(storage, S3BotoStorage):
                system_storage = FileSystemStorage(location=settings.MEDIA_ROOT)
                storage = self.get_default_storage(account)
                path = system_storage.save(
                    os.path.join(
                    media_path, sha1_filename), uploaded_file)
                file_obj = UploadedImage.objects.create(
                    uploaded_file_cache=os.path.join(settings.MEDIA_URL, path),
                    file_path=path,
                    account=self.get_account(),
                    file_name=file_name)
                upload_to_s3 = S3UploadMediaTask()
                upload_to_s3.delay(file_obj, uploaded_file)
            else:
                path = storage.save(
                    os.path.join(
                    media_path, sha1_filename), uploaded_file)
                file_obj = UploadedImage.objects.create(
                    uploaded_file=os.path.join(settings.MEDIA_URL, path),
                    file_path=path,
                    account=self.get_account(),
                    file_name=file_name)

            serializer = UploadedImageSerializer(file_obj)
            return Response(serializer.data, status=status.HTTP_200_OK)

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
        sha = self.kwargs.get(self.lookup_url_kwarg)
        instance = self.get_queryset().filter(
            Q(uploaded_file__contains=sha)\
            |Q(uploaded_file_cache__contains=sha))[0]
        return instance

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        storage = self.get_default_storage(instance.account)
        if isinstance(storage, S3BotoStorage):
            if storage.exists(instance.file_path):
                storage.delete(instance.file_path)
            else:
                try:
                # No file found on S3 delete cache file
                    os.remove(os.path.join(
                        settings.MEDIA_ROOT, instance.file_path))
                except OSError:
                    pass
        else:
            os.remove(os.path.join(settings.MEDIA_ROOT, instance.file_path))

        page_elements = PageElement.objects.filter(
            text=instance.uploaded_file)
        instance.delete()
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
