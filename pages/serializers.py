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

import os

from pages.settings import USE_S3, S3_URL
from rest_framework import serializers
from pages.models import PageElement, UploadedImage, UploadedTemplate
from django.conf import settings
#pylint: disable=no-init
#pylint: disable=old-style-class

class PageElementSerializer(serializers.ModelSerializer):

    class Meta:
        model = PageElement
        fields = ('slug', 'text')
        read_only_fields = ('slug',)

class UploadedImageSerializer(serializers.ModelSerializer):
    file_src = serializers.SerializerMethodField('get_file_url')
    file_src_temp = serializers.SerializerMethodField('get_file_temp_url')

    class Meta:
        model = UploadedImage
        fields = ('file_src', 'uploaded_file','file_src_temp', 'uploaded_file_temp', 'account', 'id', 'tags')

    def get_file_url(self, obj):#pylint: disable=no-self-use
        if obj.uploaded_file:
            if USE_S3:
                return obj.uploaded_file.url.split('?')[0].replace('/media/',S3_URL)
            else:
                return obj.uploaded_file.url.split('?')[0]
        else:
            return None

    def get_file_temp_url(self, obj):#pylint: disable=no-self-use
        if obj.uploaded_file_temp:
            return '/media/' + obj.uploaded_file_temp.name
        else:
            return None

class UploadedTemplateSerializer(serializers.ModelSerializer):

    class Meta:
        model = UploadedTemplate

