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
import logging

from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from django.db.models import Max, Q
from django.http import Http404
from rest_framework import (generics, response as api_response,
                            viewsets, status)
from rest_framework.mixins import CreateModelMixin
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.decorators import action

from ..compat import reverse
from ..helpers import ContentCut, get_extra
from ..mixins import AccountMixin, PageElementMixin, TrailMixin
from ..models import (PageElement, RelationShip, build_content_tree,
    flatten_content_tree, Sequence, EnumeratedElements)
from ..serializers import (NodeElementSerializer, PageElementSerializer,
    PageElementTagSerializer, SequenceSerializer, EnumeratedElementSerializer)
from ..utils import validate_title

LOGGER = logging.getLogger(__name__)


class PageElementAPIView(TrailMixin, generics.ListAPIView):
    """
    Lists tree of page elements matching prefix

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
            cut = self.get_cut()
            if not cut:
                cut = ContentCut()
            content_tree = build_content_tree(
                roots=None, prefix=self.full_path,
                cut=cut,
                visibility=self.visibility,
                accounts=self.owners)
            # We do not re-sort the roots such that member-only content
            # appears at the top.
            items = flatten_content_tree(content_tree, sort_by_key=False)

        results = []
        for item in items:
            searchable = get_extra(item, 'searchable', False)
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


class PageElementIndexAPIView(PageElementAPIView):
    """
    Lists tree of page elements

    **Tags: content

    **Example

    .. code-block:: http

        GET /api/content/ HTTP/1.1

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
    pass


class PageElementSearchAPIView(PageElementAPIView):
    """
    Searches page elements

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
        # XXX This code is actually not triggered because of inheritance
        # from `PageElementAPIView`.
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
    Retrieves a page element

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
    Lists editable page elements

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
        queryset = PageElement.objects.all()
        if self.account_url_kwarg in self.kwargs:
            queryset = PageElement.objects.filter(account=self.account)
        if self.path:
            queryset = queryset.filter(question__path__startswith=self.path)
        try:
            search_string = self.request.query_params.get('q', None)
            if search_string is not None:
                validate_title(search_string)
                queryset = queryset.filter(
                    Q(extra__icontains=search_string)
                    | Q(title__icontains=search_string))
        except ValidationError:
            pass
        return queryset

    def post(self, request, *args, **kwargs):
        """
        Creates a page element

        **Tags: editors

        **Example

        .. code-block:: http

            POST /api/content/editables HTTP/1.1

        .. code-block:: json

            {
                "title": "Boxes enclosures"
            }

        responds

        .. code-block:: json

            {
                "slug": "boxes-enclosures",
                "title": "Boxes enclosures"
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
        Creates a page element under a prefix

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

class SequenceAPIView(viewsets.ModelViewSet): # pylint: disable=too-many-ancestors
    """
    Manages sequences of page elements

    This API endpoint allows for the creation, modification, and deletion
    of sequences. A sequence is a collection of page elements organized
    in a specific order. Each page element in a sequence is represented
    by an enumerated element which holds the position (rank) of the page
    element in the sequence.

    Also allows adding/removing page elements from sequences.

     **Tags**: sequences
    """
    serializer_class = SequenceSerializer
    http_method_names = ['get', 'post', 'head', 'patch', 'delete', 'options']
    queryset = Sequence.objects.all().order_by('slug')
    lookup_field = 'slug'

    def get_serializer_class(self):
        if self.action:
            if self.action.lower() in ['add_element', 'remove_element']:
                return EnumeratedElementSerializer
            if self.action.lower() in ['create', 'update']:
                return SequenceSerializer
        return super().get_serializer_class()

    def list(self, request, *args, **kwargs):
        """
        - **List Sequences**

        .. code-block:: http

            GET /api/sequences HTTP/1.1

        responds

        .. code-block:: json

        "count": 1,
        "next": null,
        "previous": null,
        "results": [
            {
                "created_at": "2023-10-13T21:47:44.922545Z",
                "slug": "Sequence1",
                "title": "Sequence 1",
                "account": "admin",
                "extra": "",
                "elements": [
                    {
                        "page_element": "metal",
                        "rank": 8,
                        "min_viewing_duration": "00:00:00"
                    }
                ]
            }
        ]

        """
        return super(SequenceAPIView, self).list(
            request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        """
            - **Retrieve a Sequence**

        .. code-block:: http

            GET /api/sequences/sequence1 HTTP/1.1

        responds

        .. code-block:: json

            {
                "created_at": "2023-10-13T21:47:44.922545Z",
                "slug": "sequence1",
                "title": "Sequence 1",
                "account": "admin",
                "extra": "",
                "elements": [
                    {
                        "page_element": "metal",
                        "rank": 8,
                        "min_viewing_duration": "00:00:00"
                    }
                ]
            }

        """
        return super(SequenceAPIView, self).retrieve(
            request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        """
        - **Update a Sequence**

        .. code-block:: http

            PATCH /api/sequences/updatedsequence HTTP/1.1
            Content-Type: application/json

            {
                "slug": "updatedsequence",
                "title": "UpdatedSequence",
                "account": alice,
                "extra": "",
            }

        responds

        .. code-block:: json

            {
                "created_at": "2023-10-15T04:16:24.808028Z",
                "slug": "updatedsequence"
                "title": "UpdatedSequence",
                "account": alice,
                "extra": "",
            }
        """
        return super(SequenceAPIView, self).partial_update(
            request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        """
        - **Create a Sequence**

        .. code-block:: http

            POST /api/sequences HTTP/1.1
            Content-Type: application/json

            {
                "slug": "newsequence"
                "title": "NewSequence",
                "account": admin,
                "extra": null,

            }

        responds

        .. code-block:: json

            {
                "created_at": "2023-10-14T05:23:42.452684Z",
                "slug": "newsequence",
                "title": "NewSequence",
                "account": admin,
                "extra": null,
            }
        """
        return super(SequenceAPIView, self).create(
            request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """
        - **Delete a Sequence**

        .. code-block:: http

            POST /api/sequences/1 HTTP/1.1
            Content-Type: application/json

        responds

        .. code-block:: json

            {
            }
        """
        instance = self.get_object()
        self.perform_destroy(instance)
        return api_response.Response({'detail': 'sequence deleted'},
                                     status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def add_element(self, request, slug=None):
        """
        - **Add Element to Sequence**

        Adds an element to a sequence. Creates a new `EnumeratedElements` instance.

        .. code-block:: http

            POST /api/sequences/1/add_element HTTP/1.1
            Content-Type: application/json

            {
                "page_element": production,
                "rank": 1
            }

        responds

        .. code-block:: json

            {
                "detail": "element added"
            }
        """
        #pylint:disable=unused-argument
        sequence = self.get_object()
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            try:
                serializer.save(sequence=sequence)
                return api_response.Response({'detail': 'element added'},
                                             status=status.HTTP_200_OK)
            except IntegrityError:
                return api_response.Response({'detail':
                  'An element already exists on this rank for this sequence.'},
                  status=status.HTTP_400_BAD_REQUEST)
        return api_response.Response({'detail': 'invalid parameters'},
                                     status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def remove_element(self, request, ):
        """
        - **Remove Element from Sequence**

        Removes an element from a sequence. Requires a specified rank and page_element
        to delete the EnumeratedElements instance.

        .. code-block:: http

            POST /api/sequences/1/remove_element HTTP/1.1
            Content-Type: application/json

            {
                "page_element": production,
                "rank": 1
            }

        responds

        .. code-block:: json

            {
                "detail": "element removed"
            }

        """
        #pylint:disable=unused-argument
        sequence = self.get_object()
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            deleted, _ = EnumeratedElements.objects.filter(
                sequence=sequence,
                page_element=serializer.validated_data['page_element'],
                rank=serializer.validated_data['rank']
            ).first().delete()

            if deleted:
                return api_response.Response({'detail': 'element removed'},
                                             status=status.HTTP_200_OK)
            return api_response.Response({'detail': 'element at the specified rank '
                                                    'not found in sequence'},
                                         status=status.HTTP_404_NOT_FOUND)
        return api_response.Response({'detail': 'invalid parameters'},
                                     status=status.HTTP_400_BAD_REQUEST)
