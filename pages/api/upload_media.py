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


import json, hashlib, os

from django.core.cache import cache
from django.http import HttpResponse
from django.utils.encoding import force_text
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.parsers import FileUploadParser
from rest_framework.response import Response

from ..models import  PageElement, MediaTag
from ..mixins import AccountMixin, UploadedImageMixin


class MediaListAPIView(AccountMixin,
    UploadedImageMixin,
    APIView):

    parser_classes = (FileUploadParser,)

    def get(self, request, *args, **kwargs):
        search = request.GET.get('q')
        tags = None
        if search != '':
            tags = MediaTag.objects.filter(tag__startswith=search)\
                .values_list('media_url', flat=True)
        account = self.get_account()
        storage = self.get_default_storage(account)
        storage_cache = self.get_cache_storage(account)
        if storage:
            return Response(
                self.list_media(storage, tags))
        else:
            return Response(
                self.list_media(storage_cache, tags))

    def post(self, request, *args, **kwargs):
        #pylint: disable=unused-argument,too-many-locals
        uploaded_file = request.FILES['file']
        sha1 = hashlib.sha1(uploaded_file.read()).hexdigest()

        # Store filenames with forward slashes, even on Windows
        file_name = force_text(uploaded_file.name.replace('\\', '/'))
        sha1_filename = sha1 + os.path.splitext(file_name)[1]
        account = self.get_account()
        storage = self.get_default_storage(account)
        storage_cache = self.get_cache_storage(account)
        result = {}
        if storage.exists(sha1_filename) or storage_cache.exists(sha1_filename):
            result = {
                "message": "%s is already in the gallery." % file_name}
            response_status = status.HTTP_200_OK
        else:
            storage_cache.save(sha1_filename, uploaded_file)
            response_status = status.HTTP_201_CREATED
        result.update({'file_src': storage_cache.url(sha1_filename)})
        return Response(result, status=response_status)


class MediaUpdateDestroyAPIView(
    AccountMixin,
    UploadedImageMixin,
    APIView):

    lookup_url_kwarg = 'slug'

    def patch(self, request, *args, **kwargs):
        #pylint: disable=unused-argument
        file_obj = self.kwargs.get(self.lookup_url_kwarg)
        account = self.get_account()
        storage = self.get_default_storage(self.get_account())
        tags = self.request.DATA.get('tags', "")
        media_obj = None
        for tag in tags.split(" "):
            if storage:
                media_obj = self.get_media(storage, [file_obj])
            else:
                cache_storage = self.get_cache_storage(account)
                if cache_storage:
                    media_obj = self.get_media(storage, [file_obj])
            MediaTag.objects.get_or_create(
                tag=tag, media_url=media_obj['file_src'])
        return Response({}, status=status.HTTP_200_OK)

    def get(self, request, *args, **kwargs):
        file_obj = self.kwargs.get(self.lookup_url_kwarg)
        account = self.get_account()
        storage = self.get_default_storage(self.get_account())
        if storage:
            media_obj = self.get_media(storage, [file_obj])
            tags = MediaTag.objects.filter(media_url=media_obj['file_src'])\
                    .values_list('tag', flat=True)
            media_obj['tags'] = " ".join(tags)
            return Response(media_obj)
        else:
            cache_storage = self.get_cache_storage(account)
            if cache_storage:
                media_obj = self.get_media(storage, [file_obj])
                tags = MediaTag.objects.filter(media_url=media_obj['file_src'])\
                    .values_list('tag', flat=True)
                media_obj['tags'] = "".join(tags)
                return Response(media_obj)
        return Response({})

    def delete(self, request, *args, **kwargs):
        #pylint: disable=unused-argument
        file_obj = self.kwargs.get(self.lookup_url_kwarg)
        account = self.get_account()
        storage = self.get_default_storage(self.get_account())
        media_url = ""
        media_obj = None
        deleted = False
        if storage:
            media_obj = self.get_media(storage, [file_obj])
            if media_obj and storage.exists(media_obj['media']):
                media_url = media_obj['file_src']
                storage.delete(media_obj['media'])
                deleted = True

        if not deleted:
            cache_storage = self.get_cache_storage(account)
            if cache_storage:
                media_obj = self.get_media(cache_storage, [file_obj])
                if media_obj and cache_storage.exists(media_obj['media']):
                    media_url = media_obj['file_src']
                    cache_storage.delete(media_obj['media'])

        MediaTag.objects.filter(media_url=media_url).delete()
        PageElement.objects.filter(text=media_url).delete()
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
