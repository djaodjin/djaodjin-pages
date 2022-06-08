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
import logging

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max, Q
from django.http import Http404
from rest_framework import generics, response as api_response
from rest_framework.mixins import CreateModelMixin
from rest_framework.filters import OrderingFilter, SearchFilter

from ..compat import reverse
from ..helpers import ContentCut
from ..mixins import AccountMixin, PageElementMixin, TrailMixin
from ..models import (PageElement, RelationShip, build_content_tree,
    flatten_content_tree)
from ..serializers import (NodeElementSerializer, PageElementSerializer,
    PageElementTagSerializer)
from ..utils import validate_title

LOGGER = logging.getLogger(__name__)


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

    @property
    def visibility(self):
        return None

    @property
    def owners(self):
        return None

    def attach(self, elements):
        #pylint:disable=no-self-use
        return elements

    def get_cut(self):
        cut_param = self.request.query_params.get('cut')
        return ContentCut(cut_param) if cut_param else None

    def get_results(self):
        if self.element:
            content_tree = build_content_tree(
                roots=[self.element], prefix=self.full_path,
                cut=self.get_cut(),
                visibility=self.visibility,
                accounts=self.owners)
            items = flatten_content_tree(
                content_tree, sort_by_key=False, depth=-1)
            items.pop(0)
        else:
            content_tree = build_content_tree(
                roots=None, prefix=self.full_path,
                cut=self.get_cut(),
                visibility=self.visibility,
                accounts=self.owners)
            # We do not re-sort the roots such that member-only content
            # appears at the top.
            items = flatten_content_tree(content_tree, sort_by_key=False)

        results = []
        for item in items:
            extra = item.get('extra', {})
            if extra:
                searchable = extra.get('searchable', False)
                if searchable:
                    results += [item]

        return results

    def list(self, request, *args, **kwargs):
        #pylint:disable=unused-argument
        results = self.get_results()
        self.attach(results)

        # We have multiple roots so we create an unifying top-level root.
        element = self.element if self.element else PageElement()
        element.path = self.full_path
        element.results = results
        element.count = len(results)
        serializer = self.get_serializer(element)
        return api_response.Response(serializer.data)


class PageElementSearchAPIView(PageElementAPIView):
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

    def get_results(self):
        results = []
        for item in super(PageElementSearchAPIView, self).get_results():
            extra = item.get('extra', {})
            if extra:
                searchable = extra.get('searchable', False)
                if searchable:
                    results += [item]
        return results

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


class PageElementDetailAPIView(TrailMixin, generics.RetrieveAPIView):
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


class PageElementEditableListAPIView(AccountMixin, TrailMixin,
                                     generics.ListCreateAPIView):
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

    search_fields = (
        'title',
        'extra'
    )
    ordering_fields = (
        ('title', 'title'),
    )
    ordering = ('title',)

    filter_backends = (SearchFilter, OrderingFilter,)

    def get_queryset(self):
        """
        Returns a list of heading and best practices
        """
        if self.account_url_kwarg in self.kwargs:
            queryset = PageElement.objects.filter(account=self.account)
        else:
            queryset = PageElement.objects.all()
        if self.path:
            queryset = queryset.filter(question__path__startswith=self.path)
        try:
            search_string = self.request.query_params.get('q', None)
            if search_string is not None:
                validate_title(search_string)
                queryset = queryset.filter(
                    Q(extra__icontains=search_string)
                    | Q(title__icontains=search_string))
                return queryset
        except ValidationError:
            pass
        return queryset

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
        return super(PageElementEditableListAPIView, self).create(
            request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(account=self.account)


class PageElementEditableDetail(AccountMixin, TrailMixin, CreateModelMixin,
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
        self.element.results = self.element.get_relationships()
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
        with transaction.atomic():
            element = serializer.save(account=self.account)

            # Attach the element in the content DAG
            parent = self.element
            rank = RelationShip.objects.filter(
                orig_element=parent).aggregate(Max('rank')).get(
                'rank__max', None)
            rank = 0 if rank is None else rank + 1
            RelationShip.objects.create(
                orig_element=parent, dest_element=element, rank=rank)

    def get_success_headers(self, data):
        path = data.get('path').strip(self.URL_PATH_SEP) + self.URL_PATH_SEP
        return {'Location': reverse('pages_editables_element',
            args=(self.element.account, path))}

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
