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

import random, string
from django.template.defaultfilters import slugify
from rest_framework import serializers


from .models import PageElement, ThemePackage

#pylint: disable=no-init,old-style-class,abstract-method


class RelationShipSerializer(serializers.Serializer): #pylint: disable=abstract-method
    orig_elements = serializers.ListField(
        child=serializers.SlugField(), required=False
        )
    dest_elements = serializers.ListField(
        child=serializers.SlugField(), required=False
        )

class PageElementSerializer(serializers.ModelSerializer):
    slug = serializers.SlugField(required=False)
    tag = serializers.SlugField(required=False)
    orig_elements = serializers.ListField(
        child=serializers.SlugField(), required=False
        )
    dest_elements = serializers.ListField(
        child=serializers.SlugField(), required=False
        )

    class Meta:
        model = PageElement

    def get_field_names(self, declared_fields, info):
        fields = super(PageElementSerializer, self).get_field_names(
            declared_fields, info)
        for field, _ in declared_fields.iteritems():
            if not field in fields:
                fields.append(field)
        return fields

    def update(self, instance, validated_data):
        if 'title' in validated_data:
            instance.title = validated_data['title']
        if 'text' in validated_data:
            instance.text = validated_data['text']
        instance.save()
        return instance

    def create(self, validated_data):
        model_class = self.Meta.model
        instance = model_class()
        if 'title' in validated_data:
            instance.title = validated_data['title']
        if 'text' in validated_data:
            instance.text = validated_data['text']
        if 'slug' in validated_data:
            instance.slug = validated_data['slug']
        if 'account' in validated_data:
            instance.account = validated_data['account']
        elif instance.title:
            instance.slug = slugify(instance.title)
        else:
            instance.slug = ''.join(
                random.choice(string.letters) for count in range(5))
        instance.save()
        return instance


class ThemePackageSerializer(serializers.ModelSerializer):

    class Meta:
        model = ThemePackage


class MediaItemSerializer(serializers.Serializer):

    location = serializers.CharField()

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class MediaItemListSerializer(serializers.Serializer):

    items = MediaItemSerializer(many=True)
    tags = serializers.ListField(
        child=serializers.CharField(allow_blank=True),
        required=False)

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class EditionFileSerializer(serializers.Serializer):
    themepackage = serializers.SlugField()
    filepath = serializers.CharField()
    body = serializers.CharField(allow_blank=True)
