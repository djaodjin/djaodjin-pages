# Copyright (c) 2025, Djaodjin Inc.
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
from rest_framework import serializers


from . import settings
from .compat import gettext_lazy as _, is_authenticated
from .models import (Comment, Follow, PageElement, Vote, Sequence,
    EnumeratedElements)

#pylint: disable=abstract-method


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


class NodeElementCreateSerializer(NodeElementSerializer):
    """
    Serializer to create a PageElement as a node in a content tree
    """
    title = serializers.CharField(required=True,
        help_text=_("Title of the page element"))

    class Meta(NodeElementSerializer.Meta):
        """
        Same fields as `NodeElementSerializer`
        """


class PageElementSerializer(serializers.ModelSerializer):
    """
    Serializes a short summary of a `PageElement`
    """
    slug = serializers.SlugField(required=False,
        help_text=_("Unique identifier that can be used in URL paths"))
    account = serializers.SlugRelatedField(read_only=True, required=False,
        slug_field=settings.ACCOUNT_LOOKUP_FIELD,
        help_text=_("Account that can edit the page element"))
    picture = serializers.CharField(required=False, allow_null=True,
        help_text=_("Picture icon that can be displayed alongside the title"))
    content_format = serializers.ChoiceField(
        choices=PageElement.FORMAT_CHOICES,
        required=False,
        help_text=_("Format of the content, HTML or MD"))
    extra = serializers.SerializerMethodField(required=False, allow_null=True,
        help_text=_("Extra meta data (can be stringify JSON)"))
    nb_upvotes = serializers.IntegerField(required=False,
        help_text=_("Number of times the content has been upvoted"))
    nb_followers = serializers.IntegerField(required=False,
        help_text=_("Number of followers notified when content is updated"))
    # The following fields will be set when a request user is authenticated.
    upvote = serializers.SerializerMethodField(required=False, allow_null=True,
        help_text=_("Set to true when the request user upvoted the content"))
    follow = serializers.SerializerMethodField(required=False, allow_null=True,
        help_text=_("Set to true when the request user follows the content"))
    last_read_at = serializers.SerializerMethodField(
        required=False, read_only=True,
        help_text=_("Last time the PageElement was read"))
    nb_comments_since_last_read = serializers.SerializerMethodField(
        required=False, read_only=True,
        help_text=_("Number of comments since last read"))

    class Meta:
        model = PageElement
        fields = ('slug', 'picture', 'title', 'content_format',
            'text_updated_at', 'reading_time', 'lang', 'account', 'extra',
            'nb_upvotes', 'nb_followers', 'upvote', 'follow',
            'last_read_at', 'nb_comments_since_last_read')
        read_only_fields = ('slug', 'account', 'text_updated_at',
            'nb_upvotes', 'nb_followers', 'upvote', 'follow',
            'last_read_at', 'nb_comments_since_last_read')

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
                if hasattr(data, 'vote'):
                    return data.vote
                vote = Vote.objects.filter(
                    user=request.user, element=data).first()
                return vote and vote.vote == Vote.UP_VOTE
        return None

    def get_follow(self, data):
        request = self.context.get('request')
        if request and is_authenticated(request):
            if isinstance(data, PageElement):
                if hasattr(data, 'follow'):
                    return data.follow
                return Follow.objects.filter(
                    user=request.user, element=data).exists()
        return None

    def get_last_read_at(self, data):
        request = self.context.get('request')
        if request and is_authenticated(request):
            if isinstance(data, PageElement):
                if hasattr(data, 'nb_comments_since_last_read'):
                    return data.nb_comments_since_last_read
                last_read_at = Follow.objects.filter(
                    user=request.user, element=data).values(
                    'last_read_at').first()
                return last_read_at
        return None

    def get_nb_comments_since_last_read(self, data):
        request = self.context.get('request')
        if request and is_authenticated(request):
            if isinstance(data, PageElement):
                if hasattr(data, 'nb_comments_since_last_read'):
                    return data.nb_comments_since_last_read
                last_read_at_qs = self.get_last_read_at(data)
                comment_kwargs = {}
                if last_read_at_qs:
                    last_read_at = last_read_at_qs.get('last_read_at')
                    if last_read_at:
                        comment_kwargs.update({
                            'element__text_updated_at__gt': last_read_at
                        })
                nb_comments = Comment.objects.filter(
                    user=request.user, element=data, **comment_kwargs).count()
                return nb_comments
        return None


class PageElementDetailSerializer(PageElementSerializer):
    """
    Serializes details of a `PageElement`
    """
    path = serializers.SerializerMethodField(
        help_text=_("path from the root of content tree"))
    text = serializers.CharField(
        required=False,
        help_text=_("Long description of the page element"))
    html_formatted = HTMLField(required=False,
        html_tags=settings.ALLOWED_TAGS,
        html_attributes=settings.ALLOWED_ATTRIBUTES,
        help_text=_("Text field formatted as HTML"))
    count = serializers.IntegerField(required=False)
    results = serializers.ListField(required=False,
        child=NodeElementSerializer())

    class Meta(PageElementSerializer.Meta):
        fields = PageElementSerializer.Meta.fields + (
            'path', 'text', 'html_formatted',
            'count', 'results')
        read_only_fields = PageElementSerializer.Meta.read_only_fields + (
            'path', 'html_formatted',
            'count', 'results')

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

    def to_internal_value(self, data):
        data = data.copy()
        content_format = data.get('content_format')
        if content_format == 'HTML':
            # If content_format is HTML, we sanitize the text using
            # HTMLField
            html_field = HTMLField(html_tags=settings.ALLOWED_TAGS,
                                   html_attributes=settings.ALLOWED_ATTRIBUTES)
            data['text'] = html_field.to_internal_value(data['text'])
        return super(PageElementDetailSerializer, self).to_internal_value(data)


class UserNewsSerializer(PageElementSerializer):
    """
    Serializer for news updates
    """
    descr = HTMLField(required=False,
        html_tags=settings.ALLOWED_TAGS,
        html_attributes=settings.ALLOWED_ATTRIBUTES,
        help_text=_("first paragraph of HTML-formatted content"))

    class Meta(PageElementSerializer.Meta):
        fields = PageElementSerializer.Meta.fields + ('descr',)
        read_only_fields = PageElementSerializer.Meta.read_only_fields + (
            'descr',)


class PageElementTagSerializer(serializers.ModelSerializer):

    class Meta:
        model = PageElement
        fields = ('tag',)


class EnumeratedElementSerializer(serializers.ModelSerializer):
    """
    Serializes an EnumeratedElement
    """

    content = serializers.SlugRelatedField(
        queryset=PageElement.objects.all(),
        slug_field="slug",
        help_text=_("Page element the enumerated element is for"),
        required=True)
    certificate = serializers.BooleanField(
        write_only=True,
        default=False,
        help_text=_("Field to indicate if the PageElement being added "
                    "to the Sequence is a Certificate"))

    class Meta:
        model = EnumeratedElements
        fields = ('content', 'rank', 'min_viewing_duration', 'certificate')

    def create(self, validated_data):
        validated_data.pop('certificate', None)

        return EnumeratedElements.objects.create(**validated_data)


class SequenceSerializer(serializers.ModelSerializer):
    """
    Serializes a Sequence object
    """
    account = serializers.SlugRelatedField(required=False, read_only=True,
        slug_field=settings.ACCOUNT_LOOKUP_FIELD,
        help_text=_("Account that can edit the sequence"))

    class Meta:
        model = Sequence
        fields = ('created_at', 'slug', 'title', 'account', 'has_certificate',
                   'extra')
        read_only_fields = ('created_at', 'account',)

    @staticmethod
    def get_elements(obj):
        return EnumeratedElementSerializer(
            obj.sequence_enumerated_elements.all().order_by('rank'),
            many=True).data


class SequenceUpdateSerializer(SequenceSerializer):
    """
    Serializer to create a `Sequence`
    """
    slug = serializers.SlugField(required=False,
        help_text=_("Unique identifier for the sequence"))

    class Meta(SequenceSerializer.Meta):
        fields = SequenceSerializer.Meta.fields


class SequenceCreateSerializer(SequenceUpdateSerializer):
    """
    Serializer to create a `Sequence`
    """
    title = serializers.CharField(required=True,
        help_text=_("Title of the sequence"))

    class Meta(SequenceUpdateSerializer.Meta):
        fields = SequenceUpdateSerializer.Meta.fields


class EnumeratedProgressSerializer(EnumeratedElementSerializer):
    """
    Serializes a EnumeratedProgress object
    """
    viewing_duration = serializers.DurationField(
        help_text=_("Time spent by the user on the material (in hh:mm:ss)"))

    class Meta(EnumeratedElementSerializer.Meta):
        fields =  EnumeratedElementSerializer.Meta.fields + (
            'viewing_duration',)
        read_only_fields = ('content', 'rank', 'min_viewing_duration',
            'certificate', 'viewing_duration',)


class ValidationErrorSerializer(NoModelSerializer):
    """
    Details when an error occurs
    """
    detail = serializers.CharField(help_text=_("Describes the reason for"\
        " the error in plain text"))
