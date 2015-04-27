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


from django.db.models import Q
from rest_framework import serializers

from pages.models import (
    PageElement,
    UploadedImage,
    UploadedTemplate)
#pylint: disable=no-init
#pylint: disable=old-style-class

class PageElementSerializer(serializers.ModelSerializer):

    class Meta:
        model = PageElement
        fields = ('slug', 'text', 'image')
        read_only_fields = ('slug',)

    @staticmethod
    def set_image_field(instance, validated_data):
        if instance.slug.startswith('djmedia-'):
            img = validated_data.get('text')
            uploadimage = UploadedImage.objects.filter(Q(
                    uploaded_file=img)|Q(uploaded_file_cache=img),
                    account=instance.account)
            if uploadimage.count() > 0:
                instance.image = uploadimage.first()
        return instance

    def update(self, instance, validated_data):
        return super(PageElementSerializer, self).update(
            self.set_image_field(instance, validated_data), validated_data)

    def create(self, validated_data):
        instance = super(PageElementSerializer, self).create(validated_data)
        instance = self.set_image_field(instance, validated_data)
        instance.save()
        return instance


class UploadedImageSerializer(serializers.ModelSerializer):
    sha1 = serializers.SerializerMethodField()
    file_src = serializers.SerializerMethodField()

    class Meta:
        model = UploadedImage
        fields = (
            'file_src',
            'account',
            'tags',
            'sha1')

    @staticmethod
    def get_file_src(obj):
        return obj.get_src_file()

    @staticmethod
    def get_sha1(obj):
        return obj.get_sha1()


class UploadedTemplateSerializer(serializers.ModelSerializer):

    class Meta:
        model = UploadedTemplate

