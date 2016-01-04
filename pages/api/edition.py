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

#pylint: disable=no-init,no-member
#pylint: disable=old-style-class,maybe-no-member
import bleach, random

from django.http import Http404
from django.template.defaultfilters import slugify
from django.core.exceptions import ImproperlyConfigured

from rest_framework.mixins import CreateModelMixin
from rest_framework import generics
from rest_framework import status
from rest_framework.response import Response

from pages.models import PageElement
from pages.serializers import PageElementSerializer
from pages.mixins import AccountMixin
from pages.compat import import_string
from pages.settings import (
    ALLOWED_TAGS,
    ALLOWED_ATTRIBUTES,
    ALLOWED_STYLES,
    PAGELEMENT_SERIALIZER)

class PageElementMixin(object):

    def get_serializer_class(self):
        try:
            serializer_class = import_string(PAGELEMENT_SERIALIZER)
            if issubclass(serializer_class, PageElementSerializer):
                return serializer_class
            else:
                raise ImproperlyConfigured(
                    '"%s" should be a subclass of \
                    pages.serializers.PageElementSerializer' % (
                        PAGELEMENT_SERIALIZER))
        except ImportError  as err:
            raise ImproperlyConfigured(
                'Error importing serializer %s: "%s"' % (
                    PAGELEMENT_SERIALIZER, err))

    @staticmethod
    def slugify_title(title):
        slug_base = slugify(title)
        slug = slug_base
        while PageElement.objects.filter(slug=slug).count() > 0:
            suffix = ''.join(
                random.choice('0123456789') for count in range(5))
            slug = "%s-%s" % (slug_base, suffix)
        return slug

    def sanitize(self, serializer, slugit=True):
        # Save a clean version of html.
        if 'text' in serializer.validated_data:
            serializer.validated_data['text'] = bleach.clean(
                serializer.validated_data['text'],
                tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES,
                styles=ALLOWED_STYLES, strip=False)
        if 'title' in serializer.validated_data:
            # Sanitize title disallow any tags.
            serializer.validated_data['title'] = bleach.clean(
                serializer.validated_data['title'],
                tags=[], attributes={},
                styles=[], strip=True)
            if slugit:
                serializer.validated_data['slug'] = self.slugify_title(
                    serializer.validated_data['title'])
        return serializer


class PagesElementListAPIView(
    PageElementMixin,
    AccountMixin,
    generics.ListCreateAPIView):

    def get_queryset(self):
        # Typeahead query
        queryset = PageElement.objects.filter(account=self.account)
        tag = self.request.query_params.get('tag', None)
        search_string = self.request.query_params.get('q', None)
        if search_string is not None:
            queryset = queryset.filter(tag=tag, title__contains=search_string)
        return queryset

    def get_response_data(self, serializer):
        serializer = self.get_serializer_class()(self.new_element)
        return serializer.data

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=False)
        serializer = self.sanitize(serializer, slugit=False)
        if 'slug' in serializer.validated_data:
            slug = serializer.validated_data['slug']
        else:
            slug = self.slugify_title(
                serializer.validated_data['title'])
        self.new_element, created = PageElement.objects.get_or_create(
                slug=slug,
                defaults={
                    'slug': self.slugify_title(
                        serializer.validated_data['title']),
                    'title': serializer.validated_data['title'],
                    'text': "No description.",
                    'tag': serializer.validated_data['tag']
                }
            )

        relation_created = self.create_relationships(serializer)
        if created or relation_created:
            response_status = status.HTTP_201_CREATED
        else:
            response_status = status.HTTP_200_OK

        # headers = self.get_success_headers(serializer.data)
        data = self.get_response_data(serializer)
        return Response(
            data, status=response_status)

    def create_relationships(self, serializer):
        created = False
        if 'orig_elements' in serializer.validated_data:
            orig_elements = serializer.validated_data['orig_elements']
            print orig_elements
            for orig_element in orig_elements:
                orig_element = PageElement.objects.get(
                    slug=orig_element)
                _, relation_created = orig_element.add_relationship(
                    self.new_element, serializer.validated_data['tag']
                    )
                created = created or relation_created

        if 'dest_elements' in serializer.validated_data:
            dest_elements = serializer.validated_data['dest_elements']
            for dest_element in dest_elements:
                dest_element = PageElement.objects.get(
                    slug=dest_element)
                _, relation_created = self.new_element.add_relationship(
                    dest_element, serializer.validated_data['tag'])
        return created


class PageElementDetail(PageElementMixin, AccountMixin, CreateModelMixin,
                        generics.RetrieveUpdateDestroyAPIView):
    """
    Create or Update an editable element on a ``PageElement``.
    """
    lookup_field = 'slug'
    lookup_url_kwarg = 'slug'

    def get_queryset(self):
        kwargs = {self.lookup_field: self.kwargs.get(self.lookup_url_kwarg)}
        return PageElement.objects.filter(
            account=self.account, **kwargs)

    def perform_update(self, serializer):
        serializer = self.sanitize(serializer, slugit=False)
        serializer.save()

    def perform_create(self, serializer):
        serializer = self.sanitize(serializer)
        return serializer.save(
            slug=self.kwargs.get(self.lookup_url_kwarg),
            account=self.account)

    def update_or_create(self, request, *args, **kwargs):
        #pylint: disable=unused-argument
        """
        Update or create a ``PageElement`` with a text overlay
        of the default text present in the HTML template.
        """
        try:
            return self.update(request)
        except Http404:
            return self.create(request)

    def put(self, request, *args, **kwargs):
        return self.update_or_create(request, *args, **kwargs)
