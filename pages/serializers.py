# Copyright (c) 2023, Djaodjin Inc.
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

import json, markdown

import bleach
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404


from . import settings
from .compat import gettext_lazy as _, is_authenticated
from .models import (Comment, Follow, PageElement, Vote,
                     Sequence, EnumeratedElements, EnumeratedProgress,
                     SequenceProgress)

#pylint: disable=no-init,abstract-method


class HTMLField(serializers.CharField):

    def __init__(self, **kwargs):
        self.html_tags = kwargs.pop('html_tags', [])
        self.html_attributes = kwargs.pop('html_attributes', {})
        self.html_strip = kwargs.pop('html_strip', False)
        super(HTMLField, self).__init__(**kwargs)

    def to_internal_value(self, data):
        return super(HTMLField, self).to_internal_value(
            bleach.clean(data,
                tags=self.html_tags,
                attributes=self.html_attributes,
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
    text = HTMLField(required=False,
        html_tags=settings.ALLOWED_TAGS,
        html_attributes=settings.ALLOWED_ATTRIBUTES,
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
    path = serializers.SerializerMethodField(read_only=True, allow_null=True,
        help_text=_("path from the root of content tree"))
    indent = serializers.SerializerMethodField(required=False, allow_null=True,
        help_text=_("level in the content tree"))
    account = serializers.SlugRelatedField(read_only=True, required=False,
        slug_field=settings.ACCOUNT_LOOKUP_FIELD,
        help_text=_("Account that can edit the page element"))
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
            extra = obj.extra
        except AttributeError:
            extra = obj.get('extra', {})
        if not isinstance(extra, dict):
            try:
                return json.loads(extra)
            except (TypeError, ValueError):
                pass
        return extra

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
        help_text=_("Account that can edit the page element"))
    picture = serializers.CharField(required=False, allow_null=True,
        help_text=_("Picture icon that can be displayed alongside the title"))
    content_format = serializers.ChoiceField(
        choices=PageElement.FORMAT_CHOICES,
        required=False)
    text = serializers.CharField(
        required=False,
        help_text=_("Long description of the page element"))
    html_formatted = serializers.SerializerMethodField()
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
        fields = ('path', 'slug', 'picture', 'title', 'content_format',
            'text', 'reading_time', 'lang', 'account', 'extra',
            'nb_upvotes', 'nb_followers', 'upvote', 'follow',
            'count', 'results', 'html_formatted')
        read_only_fields = ('path', 'slug', 'account',
            'nb_upvotes', 'nb_followers', 'upvote', 'follow',
            'count', 'results', 'html_formatted')

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

    @staticmethod
    def get_html_formatted(obj):
        return markdown.markdown(obj.text, extensions=['tables']) \
            if obj.content_format == 'MD' else obj.text

    def to_internal_value(self, data):
        data = data.copy()
        content_format = data.get('content_format')
        if content_format == 'HTML':
            # If content_format is HTML, we sanitize the text using
            # HTMLField
            html_field = HTMLField(html_tags=settings.ALLOWED_TAGS,
                                   html_attributes=settings.ALLOWED_ATTRIBUTES)
            data['text'] = html_field.to_internal_value(data['text'])
        return super().to_internal_value(data)


class PageElementTagSerializer(serializers.ModelSerializer):

    class Meta:
        model = PageElement
        fields = ('tag',)


class EnumeratedElementSerializer(serializers.ModelSerializer):
    """
    Serializes an EnumeratedElement
    """

    page_element = serializers.SlugRelatedField(
        queryset=PageElement.objects.all(),
        slug_field="slug",
        help_text=_("Page element the enumerated element is for"),
        required=False)
    certificate = serializers.BooleanField(
        write_only=True, default=False,
        help_text=_("Field to indicate if the PageElement being added "
                    "to the Sequence is a Certificate"))

    class Meta:
        model = EnumeratedElements
        fields = ('page_element', 'rank', 'min_viewing_duration', 'certificate')

    def create(self, validated_data):
        validated_data.pop('certificate', None)

        return EnumeratedElements.objects.create(**validated_data)


class SequenceSerializer(serializers.ModelSerializer):
    """
    Serializes a Sequence object
    """
    elements = serializers.SerializerMethodField()
    account = serializers.SlugRelatedField(
        queryset=get_user_model().objects.all(),
        slug_field=settings.ACCOUNT_LOOKUP_FIELD,
        help_text=_("Account the sequence belongs to"),
        required=False)

    class Meta:
        model = Sequence
        fields = (('created_at', 'slug', 'title', 'account', 'has_certificate',
                   'extra') + ('elements',))

    @staticmethod
    def get_elements(obj):
        return EnumeratedElementSerializer(
            obj.sequence_enumerated_elements.all().order_by('rank'),
            many=True).data

class EnumeratedProgressSerializer(serializers.ModelSerializer):
    """
    Serializes a EnumeratedProgress object
    """
    class Meta:
        model = EnumeratedProgress
        fields = ('created_at', 'rank', 'viewing_duration')

class EnumeratedProgressCreateSerializer(serializers.ModelSerializer):
    sequence_slug = serializers.SlugRelatedField(
        slug_field='slug',
        queryset=Sequence.objects.all(),
        source='progress.sequence')
    username = serializers.SlugRelatedField(
        slug_field='username',
        queryset=get_user_model().objects.all(),
        source='progress.user')

    class Meta:
        model = EnumeratedProgress
        fields = ['sequence_slug', 'username', 'rank', 'viewing_duration', 'last_ping_time']

    def create(self, validated_data):
        progress_data = validated_data.pop('progress')
        sequence = Sequence.objects.get(
            slug=progress_data['sequence'])
        user = get_user_model().objects.get(
            username=progress_data['user'])
        with transaction.atomic():
            progress, created = SequenceProgress.objects.get_or_create(
                sequence=sequence,
                user=user)
            enumerated_progress = EnumeratedProgress.objects.create(
                progress=progress,
                **validated_data)
        return enumerated_progress

class EnumeratedProgressPingSerializer(serializers.ModelSerializer):
    """
    Serializes a EnumeratedProgress object to update its last_ping_time
    """
    class Meta:
        model = EnumeratedProgress
        fields = ('created_at', 'viewing_duration', 'last_ping_time')

class AttendanceInputSerializer(serializers.Serializer):
    """
    Serializer to validate input to mark users' attendance
    to a LiveEvent(LiveEventAttendanceAPIView)
    """
    sequence = serializers.SlugField()
    username = serializers.CharField()
    rank = serializers.IntegerField()

    def validate_sequence(self, value):
        return get_object_or_404(Sequence, slug=value)

    def validate_username(self, value):
        return get_object_or_404(get_user_model(), username=value)
