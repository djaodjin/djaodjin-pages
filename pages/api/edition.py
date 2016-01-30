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
import random

from django.http import Http404
from django.template.defaultfilters import slugify
from django.core.exceptions import ImproperlyConfigured
from django.core.validators import validate_slug
from django.core.exceptions import ValidationError
from rest_framework.mixins import CreateModelMixin
from rest_framework import generics

from ..models import PageElement
from ..serializers import PageElementSerializer
from ..mixins import AccountMixin
from ..compat import import_string
from ..utils import validate_title
from ..settings import (
    PAGELEMENT_SERIALIZER)

class PageElementMixin(object):

    def get_serializer_class(self): #pylint:disable=no-self-use
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
        slug_max_length = PageElement._meta.get_field('slug').max_length #pylint: disable=protected-access

        slug = slugify(title)
        if len(slug) > slug_max_length:
            slug = slug[:slug_max_length]

        slug_base = slug
        if len(slug_base) > slug_max_length - 6:
            slug_base = slug_base[:slug_max_length - 6]

        while PageElement.objects.filter(slug=slug).count() > 0:
            suffix = ''.join(
                random.choice('0123456789') for count in range(5))
            slug = "%s-%s" % (slug_base, suffix)
        return slug

    @staticmethod
    def create_relationships(page_element, serializer):
        created = False
        if 'orig_elements' in serializer.validated_data:
            orig_elements = serializer.validated_data['orig_elements']
            for orig_element in orig_elements:
                orig_element = PageElement.objects.get(
                    slug=orig_element)
                _, relation_created = orig_element.add_relationship(
                    page_element, serializer.validated_data['tag']
                    )
                created = created or relation_created

        if 'dest_elements' in serializer.validated_data:
            dest_elements = serializer.validated_data['dest_elements']
            for dest_element in dest_elements:
                dest_element = PageElement.objects.get(
                    slug=dest_element)
                _, relation_created = page_element.add_relationship(
                    dest_element, serializer.validated_data['tag'])

                created = created or relation_created
        return created


class PagesElementListAPIView(PageElementMixin, AccountMixin,
    generics.ListAPIView):

    def get_queryset(self):
        try:
            queryset = PageElement.objects.filter(account=self.account)
            search_string = self.request.query_params.get('q', None)
            if search_string is not None:
                tag = self.request.query_params.get('tag', None)
                validate_slug(tag)
                validate_title(search_string)
                queryset = queryset.filter(tag=tag,
                    title__contains=search_string)
                return queryset
        except ValidationError:
            return []

    def get_response_data(self, serializer, created):
        serializer = self.get_serializer_class()(self.new_element)
        return serializer.data


class PageElementDetail(PageElementMixin, AccountMixin, CreateModelMixin,
                        generics.RetrieveUpdateDestroyAPIView):
    """
    Create or Update an editable element on a ``PageElement``.
    """
    lookup_field = 'slug'
    lookup_url_kwarg = 'slug'

    def get_object(self):
        obj = None
        try:
            obj = super(PageElementDetail, self).get_object()
        except Http404:
            if hasattr(self, 'serializer_data'):
                obj = PageElement.objects.get(slug=self.serializer_data['slug'])
            else:
                raise Http404
        return obj

    def get_queryset(self):
        kwargs = {self.lookup_field: self.kwargs.get(self.lookup_url_kwarg)}
        return PageElement.objects.filter(
            account=self.account, **kwargs)

    def get_response_data(self, serializer): #pylint: disable=no-self-use
        return serializer.data

    def perform_create(self, serializer):
        if not 'slug' in serializer.validated_data and\
            'title' in serializer.validated_data:
            serializer.validated_data['slug'] = self.slugify_title(
                serializer.validated_data['title'])
        serializer.save(
            account=self.account)
        self.serializer_data = serializer.data
        self.create_relationships(self.get_object(), serializer)
        self.response_data = self.get_response_data(serializer, True)

    def perform_update(self, serializer):
        serializer.save()
        self.create_relationships(self.get_object(), serializer)
        self.response_data = self.get_response_data(serializer, False)

    def update(self, request, *args, **kwargs):
        response = super(PageElementDetail, self).update(request,
            *args, **kwargs)
        response.data = self.response_data
        return response

    def create(self, request, *args, **kwargs):
        response = super(PageElementDetail, self).create(request,
            *args, **kwargs)
        response.data = self.response_data
        return response

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
