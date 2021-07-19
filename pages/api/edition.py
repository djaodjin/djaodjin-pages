# Copyright (c) 2021, Djaodjin Inc.
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
import logging

from django.http import Http404
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from rest_framework import generics, response as api_response
from rest_framework.mixins import CreateModelMixin
from rest_framework.filters import SearchFilter

from .. import settings
from ..models import PageElement, build_content_tree, flatten_content_tree
from ..serializers import (NodeElementSerializer, PageElementSerializer,
    PageElementTagSerializer)
from ..mixins import AccountMixin, PageElementMixin, TrailMixin
from ..utils import validate_title


LOGGER = logging.getLogger(__name__)


class PageElementSearchAPIView(AccountMixin, generics.ListAPIView):
    """
    Search through page elements

    **Tags: content

    **Example

    .. code-block:: http

        GET /api/content/search HTTP/1.1

    responds

    .. code-block:: json

        {
          "count": 1,
          "next": null,
          "previous": null,
          "results": [{
            "slug": "hello",
            "path": "/hello",
            "title": "Hello"
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
                    Q(extra__icontains=search_string)
                    | Q(title__icontains=search_string))
                return queryset
        except ValidationError:
            pass
        return []


class PageElementAPIView(TrailMixin, generics.ListAPIView):
    """
    Lists a tree of page elements

    **Tags: content

    **Example

    .. code-block:: http

        GET /api/content/boxes-and-enclosures HTTP/1.1

    responds

    .. code-block:: json

        {
          "count": 8,
          "next": null,
          "previous": null,
          "results": [
          {
            "slug": "metal",
            "path": null,
            "title": "Metal structures & equipment",
            "indent": 0
          },
          {
            "slug": "boxes-and-enclosures",
            "path": "/metal/boxes-and-enclosures",
            "title": "Boxes & enclosures",
            "indent": 1,
            "tags": [
              "industry",
              "pagebreak",
              "public",
              "scorecard"
            ]
          }
          ]
        }
    """
    serializer_class = PageElementSerializer
    queryset = PageElement.objects.all()

    def attach(self, elements):
        return elements

    def list(self, request, *args, **kwargs):
        #pylint:disable=unused-argument
        content_tree = build_content_tree(
            roots=[self.element] if self.element else None,
            prefix=self.full_path)
        results = flatten_content_tree(content_tree)
        self.attach(results)

        results.pop(0)
        self.element.path = self.full_path
        self.element.results = results
        self.element.count = len(results)
        serializer = self.get_serializer(self.element)
        return api_response.Response(serializer.data)


class PageElementDetailAPIView(AccountMixin, PageElementMixin,
                               generics.RetrieveAPIView):
    """
    Retrieves details on a page element

    **Tags: content

    **Example

    .. code-block:: http

        GET /api/content/detail/adjust-air-fuel-ratio HTTP/1.1

    responds

    .. code-block:: json

        {
            "slug": "adjust-air-fuel-ratio",
            "picture": null,
            "title": "Adjust air/fuel ratio",
            "text": "<h2>Background</h2><p>Some manufacturing processes may\
 involve heating operations.</p>",
            "extra": null
        }
    """
    serializer_class = PageElementSerializer

    def get_object(self):
        return self.element


class PageElementEditableListAPIView(TrailMixin, generics.ListCreateAPIView):
    """
    List editable page elements

    This API endpoint lists page elements that are owned and thus editable
    by an account.

    **Tags**: editors

    **Examples

    .. code-block:: http

        GET /api/content/editables/energy-utility/ HTTP/1.1

    responds

    .. code-block:: json

        {
            "count": 5,
            "next": null,
            "previous": null,
            "results": [
                {
                    "path": null,
                    "title": "Construction",
                    "tags": ["public"],
                    "indent": 0
                },
                {
                    "path": null,
                    "title": "Governance & management",
                    "picture": "https://assets.tspproject.org/management.png",
                    "indent": 1
                },
                {
                    "path": "/construction/governance/the-assessment\
-process-is-rigorous",
                    "title": "The assessment process is rigorous",
                    "indent": 2,
                    "environmental_value": 1,
                    "business_value": 1,
                    "profitability": 1,
                    "implementation_ease": 1,
                    "avg_value": 1
                },
                {
                    "path": null,
                    "title": "Production",
                    "picture": "https://assets.tspproject.org/production.png",
                    "indent": 1
                },
                {
                    "path": "/construction/production/adjust-air-fuel\
-ratio",
                    "title": "Adjust Air fuel ratio",
                    "indent": 2,
                    "environmental_value": 2,
                    "business_value": 2,
                    "profitability": 2,
                    "implementation_ease": 2,
                    "avg_value": 2
                }
            ]
        }
    """
    serializer_class = NodeElementSerializer
    filter_backends = (SearchFilter,)

    def get_queryset(self):
        """
        Returns a list of heading and best practices
        """
        account_url_kwarg = settings.ACCOUNT_URL_KWARG
        if account_url_kwarg in self.kwargs:
            queryset = PageElement.objects.filter(account=self.account)
        else:
            queryset = PageElement.objects.all()
        if self.path:
            queryset = queryset.filter(consumption__path__startswith=self.path)
#        queryset = queryset.annotate(
#            nb_referencing_practices=Count('consumption')).order_by('title')
        return queryset


class PageElementEditableDetail(AccountMixin, PageElementMixin,
                                CreateModelMixin,
                                generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieves an editable page element

    **Tags: editors

    **Example

    .. code-block:: http

        GET /api/content/editables/boxes-enclosures/ HTTP/1.1

    responds

    .. code-block:: json

        {
            "slug": "boxes-enclosures",
            "path": "/boxes-enclosures",
            "text": "Hello"
        }
    """
    serializer_class = PageElementSerializer

    def get_object(self):
        return self.element

    def delete(self, request, *args, **kwargs):
        """
        Deletes a page element

        **Tags: editors

        **Example

        .. code-block:: http

            DELETE /api/content/editables/boxes-enclosures/ HTTP/1.1
        """
        #pylint:disable=useless-super-delegation
        return super(PageElementEditableDetail, self).delete(
            request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """
        Creates a page element

        **Tags: editors

        **Example

        .. code-block:: http

            POST /api/content/editables/boxes-enclosures/ HTTP/1.1

        .. code-block:: json

            {
                "title": "Boxes enclosures"
            }

        responds

        .. code-block:: json

            {
                "slug": "boxes-enclosures",
                "text": "Hello"
            }

        """
        #pylint:disable=useless-super-delegation
        return super(PageElementEditableDetail, self).create(
            request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        """
        Updates a page element

        **Tags: editors

        **Example

        .. code-block:: http

            PUT /api/content/editables/boxes-enclosures/ HTTP/1.1

        .. code-block:: json

            {
                "title": "Boxes and enclosures"
            }

        responds

        .. code-block:: json

            {
                "slug": "boxes-enclosures",
                "text": "Hello"
            }
        """
        #pylint:disable=useless-super-delegation
        return super(PageElementEditableDetail, self).put(
            request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(account=self.account)

    def update(self, request, *args, **kwargs):
        with transaction.atomic():
            try:
                _ = self.element
                return super(PageElementEditableDetail, self).update(
                    request, *args, **kwargs)
            except Http404:
                pass
            return super(PageElementEditableDetail, self).create(
                request, *args, **kwargs)


class PageElementAddTags(AccountMixin, PageElementMixin,
                         generics.UpdateAPIView):
    """
    Adds tags to an editable node

    Add tags to a ``PageElement`` if they are not already present.

    **Example

    .. code-block:: http

        PUT /api/content/editables/boxes-and-enclosures/add-tags/ HTTP/1.1

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

    def get_object(self):
        return self.element

    def perform_update(self, serializer):
        curr_tags = serializer.instance.extra
        if curr_tags:
            curr_tags = curr_tags.split(',')
        else:
            curr_tags = []
        add_tags = serializer.validated_data['tag'].split(',')
        for tag in add_tags:
            if not tag in curr_tags:
                curr_tags.append(tag)
        serializer.instance.extra = ','.join(curr_tags)
        serializer.instance.save()


class PageElementRemoveTags(AccountMixin, PageElementMixin,
                            generics.UpdateAPIView):
    """
    Remove tags from an editable node

    Remove tags from a ``PageElement``.

    **Examples

    .. code-block:: http

        PUT /api/content/editables/boxes-and-enclosures/remove-tags/ HTTP/1.1

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

    def get_object(self):
        return self.element

    def perform_update(self, serializer):
        curr_tags = serializer.instance.extra
        if curr_tags:
            curr_tags = curr_tags.split(',')
        else:
            curr_tags = []
        remove_tags = serializer.validated_data['tag'].split(',')
        for tag in remove_tags:
            if tag in curr_tags:
                curr_tags.remove(tag)
        serializer.instance.extra = ','.join(curr_tags)
        serializer.instance.save()
