# Copyright (c) 2017, Djaodjin Inc.
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
#pylint: disable=no-member

import os, zipfile, hashlib, tempfile, shutil

from django.core.files import File
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.utils import six
from rest_framework import status, generics
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from boto.exception import BotoClientError

from ..mixins import UploadedImageMixin, get_bucket_name, ThemePackageMixin
from ..models import ThemePackage
from ..serializers import ThemePackageSerializer, EditionFileSerializer
from ..themes import install_theme

class ThemePackageListAPIView(UploadedImageMixin, ThemePackageMixin,
                                  generics.ListCreateAPIView):

    parser_classes = (MultiPartParser,)
    serializer_class = ThemePackageSerializer

    @staticmethod
    def get_theme_attributes(file_obj):
        if isinstance(file_obj, six.string_types):
            readable_file = open(file_obj, 'w+')
            file_obj = File(readable_file)
        theme_name = os.path.splitext(
            os.path.basename(file_obj.name))[0]
        theme_slug = theme_name + '-' +\
            hashlib.sha1(file_obj.read()).hexdigest()
        return theme_name, theme_slug

    def install_theme(self, file_obj):
        if not zipfile.is_zipfile(file_obj):
            return Response({'message': "Invalid archive"},
                status=status.HTTP_400_BAD_REQUEST)
        with zipfile.ZipFile(file_obj) as zip_file:
            install_theme(self.theme_slug, zip_file)
        theme, _ = ThemePackage.objects.get_or_create(
            slug=self.theme_slug, account=self.account,
            defaults={'name': self.theme_name})
        serializer = ThemePackageSerializer(theme)
        return Response(serializer.data,
            status=status.HTTP_201_CREATED)

    def upload_theme(self, request):
        file_obj = request.data['file']
        self.theme_name, self.theme_slug = self.get_theme_attributes(
            file_obj)
        return self.install_theme(file_obj)

    def upload_theme_from_s3(self, request):
        try:
            tmp_dir = tempfile.mkdtemp()
            file_obj = os.path.join(tmp_dir,
                request.data['file_name'])
            orig = os.path.join(request.data['s3prefix'],
                request.data['file_name'])
            file_obj = self.get_file_from_s3(get_bucket_name(self.account),
                orig, file_obj)
            self.theme_name, self.theme_slug = self.get_theme_attributes(
                file_obj)
            return self.install_theme(file_obj)
        except BotoClientError:
            return Response(
                {'message': "Theme not found"},
                    status=status.HTTP_404_NOT_FOUND)
        finally:
            shutil.rmtree(tmp_dir)

    def post(self, request, *args, **kwargs):
        if 's3prefix' in request.data:
            # if 's3prefix', callback after successful upload to S3
            return self.upload_theme_from_s3(request, *args, **kwargs)
        else:
            # Upload theme directly on the server
            return self.upload_theme(request, *args, **kwargs)


class ThemePackageAPIView(ThemePackageMixin, generics.RetrieveUpdateAPIView):

    serializer_class = ThemePackageSerializer
    lookup_url_kwarg = 'theme'
    lookup_field = 'slug'


class FileDetailAPIView(ThemePackageMixin, generics.RetrieveUpdateAPIView):

    serializer_class = EditionFileSerializer
    lookup_url_kwarg = 'theme'
    lookup_field = 'slug'

    def get_file(self):
        selected_file = None
        file_storage = None
        templates_storage = FileSystemStorage(location=self.get_templates_dir(
            self.themepackage))
        statics_storage = FileSystemStorage(location=self.get_statics_dir(
                self.themepackage))
        storages = [templates_storage, statics_storage]
        for storage in storages:
            try:
                selected_file = storage.open(self.filepath, mode='r')
                file_storage = storage
                break
            except IOError:
                pass
        return selected_file, file_storage

    @staticmethod
    def read_file(selected_file):
        content = ''
        for chunk in selected_file.chunks(10):
            content += chunk
        return content

    def get(self, request, *args, **kwargs):
        self.themepackage = self.get_object()
        self.filepath = kwargs.get('filepath', None)
        selected_file, _ = self.get_file()
        if selected_file is None:
            return Response({}, status=status.HTTP_404_NOT_FOUND)
        else:
            text = self.read_file(selected_file)
            serializer = self.get_serializer_class()({'text': text})
            return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, *args, **kwargs):
        serializer = self.get_serializer_class()(data=request.data)
        serializer.is_valid()
        self.themepackage = self.get_object()
        self.filepath = kwargs.get('filepath', None)
        selected_file, storage = self.get_file()
        if selected_file:
            storage.delete(self.filepath)
        content = ContentFile(serializer.validated_data['text'])
        storage.save(self.filepath, content)
        serializer = self.get_serializer_class()(serializer.validated_data)
        return Response(serializer.data, status=status.HTTP_200_OK)
