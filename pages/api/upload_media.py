# Copyright (c) 2014, Djaodjin Inc.
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
#pylint: disable=old-style-class,line-too-long,maybe-no-member

import os
import tempfile
import hashlib
import subprocess

from PIL import Image
from StringIO import StringIO

from django.http import HttpResponse
from django.core.cache import cache
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.exceptions import ImproperlyConfigured

try:
    import json
except ImportError:
    # Django <1.7 packages simplejson for older Python versions
    from django.utils import simplejson as json


from django.conf import settings
from django.core.files.storage import default_storage

from rest_framework import status
from rest_framework import generics
from rest_framework.parsers import FileUploadParser
from rest_framework.response import Response

from pages.models import UploadedImage, PageElement, S3Bucket
from pages.serializers import UploadedImageSerializer
from pages.settings import USE_S3, MEDIA_PATH, FFMPEG_PATH, NO_LOCAL_STORAGE, DEFAULT_STORAGE_BUCKET_NAME

from pages.mixins import AccountMixin
from pages.tasks import upload_to_s3
from storages.backends.s3boto import S3BotoStorage


class MediaListAPIView(AccountMixin, generics.ListCreateAPIView):
    serializer_class = UploadedImageSerializer
    parser_classes = (FileUploadParser,)

    @staticmethod
    def cut_off_video(video_origin):
        video = video_origin
        video.file.seek(0)
        temp_path = tempfile.gettempdir()
        with open(os.path.join(temp_path, 'temp_video'), 'wb') as new_file:
            new_file.write(video.read())
        subprocess.call([FFMPEG_PATH, '-ss', '1', '-i', os.path.join(temp_path, 'temp_video'), '-c', 'copy', '-t', '3', '-y', os.path.join(temp_path, video_origin.name), '-loglevel', 'quiet'])
        return temp_path

    @staticmethod
    def video_as_memory_file(video_origin, temp_path):
        video_string = StringIO()
        with open(os.path.join(temp_path, video_origin.name), 'rb') as video_file:
            video_string.write(video_file.read())
        c_type = video_origin.content_type
        videof = InMemoryUploadedFile(video_string, None, video_origin.name, c_type, video_string.len, None)
        videof.seek(0)
        return videof

    @staticmethod
    def resize_image(image_origin):
        image = image_origin
        image.file.seek(0) # just in case
        img_duplicate = Image.open(StringIO(image.file.read()))
        img_duplicate.thumbnail((100, 100), Image.ANTIALIAS)
        image_string = StringIO()
        img_duplicate.save(image_string, img_duplicate.format)

        # for some reason content_type is e.g. 'images/jpeg' instead of 'image/jpeg'
        c_type = image.content_type.replace('images', 'image')
        imf = InMemoryUploadedFile(image_string, None, image.name, c_type, image_string.len, None)
        imf.seek(0)
        return imf

    def get_default_storage(self):
        if self.get_account():
            try:
                bucket = S3Bucket.objects.get(account=self.get_account())
                return S3BotoStorage(bucket=bucket.bucket_name)
            except S3Bucket.DoesNotExist:
                raise ImproperlyConfigured(
                    "Account '%s' has not valid S3 bucket." % self.get_account().slug)
        else:
            return S3BotoStorage(bucket=DEFAULT_STORAGE_BUCKET_NAME)

    def post(self, request, account_slug=None, format=None, *args, **kwargs):#pylint: disable=unused-argument,redefined-builtin, too-many-locals
        uploaded_file = request.FILES['file']
        existing_file = False
        sha1_filename = hashlib.sha1(uploaded_file.read()).hexdigest() + '.' +\
            str(uploaded_file).split('.')[1].lower()
        uploaded_file.name = sha1_filename
        if USE_S3:
            path = MEDIA_PATH
            if self.get_account():
                full_path = path + self.get_account().slug + '/' + sha1_filename
            else:
                full_path = path + sha1_filename
            if self.get_default_storage().exists(full_path):
                existing_file = True
        if not existing_file:
            if USE_S3:
                if NO_LOCAL_STORAGE:
                    # Image processing
                    if uploaded_file.name.endswith(('.jpg', '.bmp', '.gif', '.jpg', '.png')):
                        in_memory_file = self.resize_image(uploaded_file)
                    # Video processing
                    elif uploaded_file.name.endswith('.mp4'):
                        temp_path = self.cut_off_video(uploaded_file)
                        in_memory_file = self.video_as_memory_file(uploaded_file, temp_path)
                    file_obj = UploadedImage(
                        uploaded_file=in_memory_file,
                        account=self.get_account()
                        )
                else:
                    file_obj = UploadedImage(
                        uploaded_file_temp=uploaded_file,
                        account=self.get_account()
                        )

            else:
                file_obj = UploadedImage(
                    uploaded_file=uploaded_file,
                    account=self.get_account())

            file_obj.save()
            if USE_S3:
                # Delay the upload to S3
                upload_to_s3.delay(uploaded_file, self.get_account(), sha1_filename)
            serializer = UploadedImageSerializer(file_obj)
        else:
            file_obj = UploadedImage.objects.get(uploaded_file=full_path)
            serializer = UploadedImageSerializer(file_obj)

        if USE_S3 and not NO_LOCAL_STORAGE:
            response = {
                'uploaded_file_temp': os.path.join(settings.MEDIA_URL, serializer.data['uploaded_file_temp']),
                'exist': existing_file,
                'id':serializer.data['id']
                }
        elif USE_S3 and NO_LOCAL_STORAGE:
            response = {
                'uploaded_file_temp': os.path.join(self.get_s3_url(file_obj), serializer.data['uploaded_file']),
                'exist': existing_file,
                'id':serializer.data['id']
                }
        else:
            response = {
                'uploaded_file_temp': os.path.join(settings.MEDIA_URL, serializer.data['uploaded_file']),
                'exist': existing_file,
                'id':serializer.data['id']
                }
        return Response(response, status=status.HTTP_200_OK)

    @staticmethod
    def get_s3_url(obj):
        if obj.account:
            return 'https://%s.s3.amazonaws.com/' % obj.account.bucket_name
        else:
            return 'https://%s.s3.amazonaws.com/' % DEFAULT_STORAGE_BUCKET_NAME

    def get_queryset(self):
        search = self.request.GET.get('search')
        queryset = UploadedImage.objects.filter(account=self.get_account()).order_by("-created_at")
        if search != '':
            queryset = UploadedImage.objects.filter(tags__contains=search).order_by("-created_at")
        return queryset


class MediaUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    model = UploadedImage
    serializer_class = UploadedImageSerializer

    @staticmethod
    def get_default_storage(obj):
        if obj.account:
            try:
                bucket = S3Bucket.objects.get(account=obj.account)
                return S3BotoStorage(bucket=bucket.bucket_name)
            except S3Bucket.DoesNotExist:
                raise ImproperlyConfigured(
                    "Account '%s' has not valid S3 bucket." % obj.account.slug)
        else:
            return S3BotoStorage(bucket=DEFAULT_STORAGE_BUCKET_NAME)

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        if USE_S3:
            # remove fil from S3 Bucket
            self.get_default_storage(instance).delete(instance.uploaded_file.name)
        else:
            # remove file from server
            os.remove(os.path.join(settings.MEDIA_ROOT, instance.uploaded_file.name))
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
