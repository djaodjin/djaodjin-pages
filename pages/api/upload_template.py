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


import os, zipfile, hashlib, tempfile, shutil

from django.conf import settings as django_settings
from django.http import Http404
from django.db.models import Q
from django.utils._os import safe_join
from rest_framework import status, generics
from rest_framework.parsers import FileUploadParser
from rest_framework.response import Response
from boto.s3.connection import S3Connection

from ..mixins import AccountMixin, UploadedImageMixin
from ..models import UploadedTemplate
from ..serializers import UploadedTemplateSerializer
from ..themes import install_theme


class UploadedTemplateMixin(AccountMixin):

    def get_queryset(self):
        queryset = UploadedTemplate.objects.filter(
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

class UploadedTemplateListAPIView(UploadedImageMixin, UploadedTemplateMixin,
                                  generics.ListCreateAPIView):

    parser_classes = (FileUploadParser,)
    serializer_class = UploadedTemplateSerializer

    def post(self, request, *args, **kwargs):
        tmp_dir = None
        if 'file' in request.data.keys():
            file_obj = request.data['file']
            theme_name = os.path.splitext(
                os.path.basename(file_obj.name))[0]
            theme_slug = theme_name + '-' +\
                hashlib.sha1(file_obj.read()).hexdigest()
        else:
            # Get zip file from S3 and install theme
            tmp_dir = tempfile.mkdtemp()
            file_obj = os.path.join(tmp_dir,
                request.data['file_name'])
            orig = os.path.join(request.data['s3prefix'],
                request.data['file_name'])

            file_obj = self.get_file_from_s3(
                self.get_bucket_name(self.account),
                orig,
                file_obj)

            if not file_obj:
                if tmp_dir:
                    shutil.rmtree(tmp_dir)
                return Response(
                    {'message': "Theme not found"},
                    status=status.HTTP_404_NOT_FOUND)

            theme_name = os.path.splitext(
                os.path.basename(file_obj))[0]
            with open(file_obj) as readable_file:
                theme_slug = theme_name + '-' +\
                    hashlib.sha1(readable_file.read()).hexdigest()

        templates_dir = safe_join(django_settings.TEMPLATE_DIRS[0], theme_slug)

        if os.path.exists(templates_dir):
            # If we do not have an instance at this point, the directory
            # might still exist and belong to someone else when pages
            # tables are split amongst multiple databases.
            if tmp_dir:
                shutil.rmtree(tmp_dir)
            return Response(
                {'message': "Theme already exists."},
                status=status.HTTP_403_FORBIDDEN)
        if zipfile.is_zipfile(file_obj):
            with zipfile.ZipFile(file_obj) as zip_file:
                install_theme(theme_slug, zip_file)
            theme = UploadedTemplate.objects.create(
                slug=theme_slug, name=theme_name, account=self.account)
            serializer = UploadedTemplateSerializer(theme)

            if tmp_dir:
                shutil.rmtree(tmp_dir)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response({'message': "Invalid archive"},
            status=status.HTTP_400_BAD_REQUEST)


class UploadedTemplateAPIView(UploadedTemplateMixin,
                              generics.RetrieveUpdateAPIView):

    serializer_class = UploadedTemplateSerializer
    slug_url_kwarg = 'theme'

    def get_object(self):
        try:
            return self.get_queryset().get(
                name=self.kwargs.get(self.slug_url_kwarg))
        except UploadedTemplate.DoesNotExist:
            raise Http404("theme %s not found"
                % self.kwargs.get(self.slug_url_kwarg))
