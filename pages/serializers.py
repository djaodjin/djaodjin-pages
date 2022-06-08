# Copyright (c) 2022, Djaodjin Inc.
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
from __future__ import unicode_literals

import json

import bleach
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from . import settings
from .compat import is_authenticated
from .models import Comment, Follow, PageElement, Vote

#pylint: disable=no-init,abstract-method


class HTMLField(serializers.CharField):

    def __init__(self, **kwargs):
        self.html_tags = kwargs.pop('html_tags', [])
        self.html_attributes = kwargs.pop('html_attributes', {})
        self.html_styles = kwargs.pop('html_styles', [])
        self.html_strip = kwargs.pop('html_strip', False)
        super(HTMLField, self).__init__(**kwargs)

    def to_internal_value(self, data):
        return super(HTMLField, self).to_internal_value(
            bleach.clean(data, tags=self.html_tags,
            attributes=self.html_attributes, styles=self.html_styles,
            strip=self.html_strip))


class NoModelSerializer(serializers.Serializer):

    def create(self, validated_data):
        raise RuntimeError('`create()` should not be called.')

    def update(self, instance, validated_data):
        raise RuntimeError('`update()` should not be called.')


class AssetSerializer(NoModelSerializer):

    location = serializers.CharField(
        help_text=_("URL where the asset content is stored."))
    updated_at = serializers.DateTimeField(required=False,
        help_text=_("Last date/time the asset content was updated."))


class EdgeCreateSerializer(serializers.Serializer):
    """
    Create a new edge between two ``PageElement``.

    The path specified in the URL will be aliased, mirrored or moved
    under *source*.
    When *rank* is specified, the resulting index of the aliased/mirrored/moved
    element in its parent list will be *rank*.

    The state in the UI is particularly complex. We use the *external_key*
    to log incorrect calls from the Javascript code.
    """
    source = serializers.CharField()
    rank = serializers.IntegerField(required=False)
    external_key = serializers.CharField(required=False)


class RelationShipSerializer(serializers.Serializer):
    #pylint: disable=abstract-method
    orig_elements = serializers.ListField(
        child=serializers.SlugField(), required=False
        )
    dest_elements = serializers.ListField(
        child=serializers.SlugField(), required=False
        )


class CommentSerializer(serializers.ModelSerializer):
    """
    Serializes a Comment.
    """
    text = HTMLField(html_tags=settings.ALLOWED_TAGS,
        html_attributes=settings.ALLOWED_ATTRIBUTES,
        html_styles=settings.ALLOWED_STYLES, required=False,
        help_text=_("Long description of the page element"))
    user = serializers.SlugRelatedField(read_only=True, slug_field='username')

    class Meta:
        model = Comment
        fields = ('text', 'created_at', 'user')
        read_only_fields = ('created_at', 'user')


class NodeElementSerializer(serializers.ModelSerializer):
    """
    Serializes a PageElement as a node in a content tree
    """
    path = serializers.SerializerMethodField(read_only=True, allow_null=True)
    indent = serializers.SerializerMethodField(required=False, allow_null=True)
    account = serializers.SlugRelatedField(read_only=True, required=False,
        slug_field=settings.ACCOUNT_LOOKUP_FIELD,
        help_text=("Account that can edit the page element"))
    picture = serializers.CharField(required=False, allow_null=True,
        help_text=_("Picture icon that can be displayed alongside the title"))
    extra = serializers.SerializerMethodField(required=False, allow_null=True,
        help_text=_("Extra meta data (can be stringify JSON)"))

    class Meta:
        model = PageElement
        fields = ('slug', 'path', 'indent', 'account',
                  'title', 'picture', 'extra')
        read_only_fields = ('slug', 'path', 'indent', 'account')

    @staticmethod
    def get_extra(obj):
        try:
            return obj.get('extra', {})
        except AttributeError:
            pass
        try:
            return obj.extra
        except AttributeError:
            pass
        return {}

    @staticmethod
    def get_indent(obj):
        try:
            return obj.get('indent', 0)
        except AttributeError:
            pass
        try:
            return obj.indent
        except AttributeError:
            pass
        return 0

    @staticmethod
    def get_path(obj):
        try:
            return obj.get('path', None)
        except AttributeError:
            pass
        try:
            return obj.path
        except AttributeError:
            pass
        return "/%s" % obj.slug


class PageElementSerializer(serializers.ModelSerializer):
    """
    Serializes a PageElement.
    """

    path = serializers.SerializerMethodField()
    slug = serializers.SlugField(required=False,
        help_text=_("Unique identifier that can be used in URL paths"))
    account = serializers.SlugRelatedField(read_only=True, required=False,
        slug_field=settings.ACCOUNT_LOOKUP_FIELD,
        help_text=("Account that can edit the page element"))
    picture = serializers.CharField(required=False, allow_null=True,
        help_text=_("Picture icon that can be displayed alongside the title"))
    text = HTMLField(html_tags=settings.ALLOWED_TAGS,
        html_attributes=settings.ALLOWED_ATTRIBUTES,
        html_styles=settings.ALLOWED_STYLES, required=False,
        help_text=_("Long description of the page element"))
    extra = serializers.SerializerMethodField(required=False, allow_null=True,
        help_text=_("Extra meta data (can be stringify JSON)"))
    nb_upvotes = serializers.IntegerField(required=False)
    nb_followers = serializers.IntegerField(required=False)
    upvote = serializers.SerializerMethodField(required=False, allow_null=True)
    follow = serializers.SerializerMethodField(required=False, allow_null=True)
    count = serializers.IntegerField(required=False)
    results = serializers.ListField(required=False,
        child=NodeElementSerializer())

    class Meta:
        model = PageElement
        fields = ('path', 'slug', 'picture', 'title', 'text', 'reading_time',
            'lang', 'account', 'extra',
            'nb_upvotes', 'nb_followers', 'upvote', 'follow',
            'count', 'results')
        read_only_fields = ('path', 'slug', 'account',
            'nb_upvotes', 'nb_followers', 'upvote', 'follow',
            'count', 'results')

    @staticmethod
    def get_extra(obj):
        try:
            extra = obj.extra
        except AttributeError:
            extra = obj.get('extra', {})
        if not isinstance(extra, dict):
            try:
                return json.loads(extra)
            except (TypeError, ValueError):
                pass
        return extra

    def get_upvote(self, data):
        request = self.context.get('request')
        if request and is_authenticated(request):
            if isinstance(data, PageElement):
                vote = Vote.objects.filter(
                    user=request.user, element=data).first()
                return vote and vote.vote == Vote.UP_VOTE
        return None

    def get_follow(self, data):
        request = self.context.get('request')
        if request and is_authenticated(request):
            if isinstance(data, PageElement):
                return Follow.objects.filter(
                    user=request.user, element=data).exists()
        return None

    def get_path(self, obj):
        prefix = self.context.get('prefix', "")
        if not prefix:
            parents = obj.get_parent_paths()
            if parents:
                prefix = "/".join(
                    [parent.slug for parent in parents[0][:-1]])
                if prefix:
                    prefix = "/" + prefix
                prefix = prefix + "/"
        try:
            slug = obj.slug
        except AttributeError:
            slug = obj.get('slug', "")
        return prefix + slug


class PageElementTagSerializer(serializers.ModelSerializer):

    class Meta:
        model = PageElement
        fields = ('tag',)
