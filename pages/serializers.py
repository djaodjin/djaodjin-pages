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


from rest_framework import serializers

from .models import PageElement, UploadedTemplate, RelationShip

#pylint: disable=no-init,old-style-class

class PageElementSlugSerializer(serializers.ModelSerializer):
    slug = serializers.SlugField(required=False)

    class Meta:
        model = PageElement
        fields = ('slug',)

class PageElementSerializer(serializers.ModelSerializer):
    tag = serializers.SlugField(required=False)
    orig_element = PageElementSlugSerializer(many=True, required=False)
    dest_element = PageElementSlugSerializer(many=True, required=False)

    class Meta:
        model = PageElement
        fields = ('slug', 'title', 'body',
            'tag', 'orig_element', 'dest_element')

    def update(self, instance, validated_data):
        if 'title' in validated_data:
            instance.title = validated_data['title']
        if 'body' in validated_data:
            instance.body = validated_data['body']
        instance.save()
        return instance


class RelationShipSerializer(serializers.ModelSerializer):
    title = serializers.CharField(required=False)

    class Meta:
        model = RelationShip
        fields = ('title', 'orig_element', 'dest_element', 'tag')


class UploadedTemplateSerializer(serializers.ModelSerializer):

    class Meta:
        model = UploadedTemplate


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
