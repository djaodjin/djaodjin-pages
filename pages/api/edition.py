# Copyright (c) 2017, Djaodjin Inc.
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

from django.http import Http404
from django.core.exceptions import ValidationError
from django.db.models import Q
from rest_framework.mixins import CreateModelMixin
from rest_framework import generics

from ..models import PageElement
from ..serializers import PageElementSerializer, PageElementTagSerializer
from ..mixins import AccountMixin, PageElementMixin
from ..utils import validate_title


class PagesElementListAPIView(AccountMixin, generics.ListCreateAPIView):
    """
    Lists editable nodes

    **Example

    .. code-block:: http

        GET /api/editables HTTP/1.1

    responds

    .. code-block:: json

        {
          "count": 1,
          "next": null,
          "previous": null,
          "results": [{
            "slug": "hello",
            "path": "/hello",
            "text": "Hello",
            "orig_elements": [],
            "dest_elements": []
          }]
        }
    """
    serializer_class = PageElementSerializer

    def get_queryset(self):
        try:
            queryset = PageElement.objects.filter(account=self.account)
            search_string = self.request.query_params.get('q', None)
            if search_string is not None:
                validate_title(search_string)
                queryset = queryset.filter(
                    Q(tag__icontains=search_string)
                    | Q(title__icontains=search_string))
                return queryset
        except ValidationError:
            pass
        return []

    def post(self, request, *args, **kwargs):
        """
        Creates an editable node

        **Example

        .. code-block:: http

            POST /api/editables HTTP/1.1

        .. code-block:: json

            {
            }

        responds

        .. code-block:: json

            {
            }
        """
        return super(PagesElementListAPIView, self).post(
            request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(account=self.account)


class PageElementDetail(PageElementMixin, CreateModelMixin,
                        generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieves an editable node

    **Example

    .. code-block:: http

        GET /api/editables/content-root/ HTTP/1.1

    responds

    .. code-block:: json

        {
            "slug": "content-root",
            "path": "/content-root",
            "text": "Hello",
            "orig_elements": [],
            "dest_elements": []
        }
    """
    serializer_class = PageElementSerializer

    def delete(self, request, *args, **kwargs):
        """
        Deletes an editable node
        **Example

        .. code-block:: http

            DELETE /api/editables/content-root/ HTTP/1.1
        """
        return super(PageElementDetail, self).delete(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        """
        Updates an editable node

        **Example

        .. code-block:: http

            PUT /api/editables/content-root/ HTTP/1.1

        .. code-block:: json

            {
            }

        responds

        .. code-block:: json

            {
            }
        """
        return super(PageElementDetail, self).put(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(account=self.account)

    def update(self, request, *args, **kwargs):
        try:
            _ = self.get_object()
            return super(PageElementDetail, self).update(
                request, *args, **kwargs)
        except Http404:
            pass
        return super(PageElementDetail, self).create(request, *args, **kwargs)


class PageElementAddTags(PageElementMixin, generics.UpdateAPIView):
    """
    Adds tags to an editable node

    Add tags to a ``PageElement`` if they are not already present.

    **Example

    .. code-block:: http

        PUT /api/editables/_my-element_/add-tags HTTP/1.1

    .. code-block:: json

        {
          "tag": "sometag"
        }

    responds

    .. code-block:: json

        {
        }
    """
    serializer_class = PageElementTagSerializer

    def perform_update(self, serializer):
        curr_tags = serializer.instance.tag
        if curr_tags:
            curr_tags = curr_tags.split(',')
        else:
            curr_tags = []
        add_tags = serializer.validated_data['tag'].split(',')
        for tag in add_tags:
            if not tag in curr_tags:
                curr_tags.append(tag)
        serializer.instance.tag = ','.join(curr_tags)
        serializer.instance.save()


class PageElementRemoveTags(PageElementMixin, generics.UpdateAPIView):
    """
    Remove tags from an editable node

    Remove tags from a ``PageElement``.

    **Tags: content

    **Examples

    .. code-block:: http

        PUT /api/editables/_my-element_/reomve-tags HTTP/1.1

    .. code-block:: json

        {
          "tag": "sometag"
        }

    responds

    **Examples

    .. code-block:: json

        {
        }
    """
    serializer_class = PageElementTagSerializer

    def perform_update(self, serializer):
        curr_tags = serializer.instance.tag
        if curr_tags:
            curr_tags = curr_tags.split(',')
        else:
            curr_tags = []
        remove_tags = serializer.validated_data['tag'].split(',')
        for tag in remove_tags:
            if tag in curr_tags:
                curr_tags.remove(tag)
        serializer.instance.tag = ','.join(curr_tags)
        serializer.instance.save()
