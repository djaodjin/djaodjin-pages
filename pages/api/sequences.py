# Copyright (c) 2024, Djaodjin Inc.
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

from django.db import transaction, IntegrityError
from django.template.defaultfilters import slugify
from rest_framework import response as api_response, status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.generics import (get_object_or_404, DestroyAPIView,
    ListAPIView, ListCreateAPIView, RetrieveUpdateDestroyAPIView)

from ..mixins import AccountMixin, SequenceMixin
from ..models import Sequence, EnumeratedElements
from ..serializers import (SequenceSerializer, SequenceCreateSerializer,
    EnumeratedElementSerializer)

LOGGER = logging.getLogger(__name__)


class SequencesIndexAPIView(ListAPIView):
    """
    Lists sequences of page elements

    Returns a list of {{PAGE_SIZE}} sequences available to the request user.

    The queryset can be further refined to match a search filter (``q``)
    and sorted on specific fields (``o``).

    **Tags: content

    **Example

    .. code-block:: http

         GET /api/sequences HTTP/1.1

    responds

    .. code-block:: json

        {
          "count": 1,
          "next": null,
          "previous": null,
          "results": [
            {
              "created_at": "2024-01-01T00:00:00.0000Z",
              "slug": "ghg-accounting-training",
              "title": "GHG Accounting Training",
              "account": "djaopsp",
              "has_certificate": true
            }
          ]
        }
    """
    queryset = Sequence.objects.all().order_by('slug')
    serializer_class = SequenceSerializer

    search_fields = (
        'title',
        'extra'
    )
    ordering_fields = (
        ('title', 'title'),
    )
    ordering = ('title',)

    filter_backends = (SearchFilter, OrderingFilter,)


class SequenceListCreateAPIView(AccountMixin, ListCreateAPIView):
    """
    Lists editable sequences

    Returns a list of {{PAGE_SIZE}} sequences editable by profile.

    The queryset can be further refined to match a search filter (``q``)
    and sorted on specific fields (``o``).

    **Tags: editors

    **Example

    .. code-block:: http

         GET /api/editables/alliance/sequences HTTP/1.1

    responds

    .. code-block:: json

        {
          "count": 1,
          "next": null,
          "previous": null,
          "results": [
            {
              "created_at": "2020-09-28T00:00:00.0000Z",
              "slug": "ghg-accounting-training",
              "title": "GHG Accounting Training",
              "account": "djaopsp",
              "has_certificate": true
            }
          ]
        }
    """
    serializer_class = SequenceSerializer

    search_fields = (
        'title',
        'extra'
    )
    ordering_fields = (
        ('title', 'title'),
    )
    ordering = ('title',)

    filter_backends = (SearchFilter, OrderingFilter,)


    def get_serializer_class(self):
        if self.request.method.lower() == 'post':
            return SequenceCreateSerializer
        return super(SequenceListCreateAPIView, self).get_serializer_class()


    def get_queryset(self):
        """
        Returns a list of heading and best practices
        """
        queryset = Sequence.objects.all()
        if self.account_url_kwarg in self.kwargs:
            queryset = queryset.filter(account=self.account)
        return queryset

    def post(self, request, *args, **kwargs):
        """
        Creates a sequence of page elements

        Creates a new sequence editable by profile.

        **Tags: editors

        **Example

        .. code-block:: http

            POST /api/editables/alliance/sequences HTTP/1.1

        .. code-block:: json

            {
                "slug": "ghg-accounting-training",
                "title": "GHG Accounting Training"
            }

        responds

        .. code-block:: json

            {
              "created_at": "2023-01-01T04:00:00.000000Z",
              "slug": "ghg-accounting-training",
              "title": "GHG Accounting Training",
              "account": null,
              "has_certificate": true
            }
        """
        return self.create(request, *args, **kwargs)


    def perform_create(self, serializer):
        serializer.save(account=self.account,
            slug=slugify(serializer.validated_data['title']))


class SequenceRetrieveUpdateDestroyAPIView(AccountMixin, SequenceMixin,
                                           RetrieveUpdateDestroyAPIView):
    """
    Retrieves a sequence

    **Tags: editors

    **Example

    .. code-block:: http

        GET /api/editables/alliance/sequences/ghg-accounting-training HTTP/1.1

    responds

    .. code-block:: json

        {
            "created_at": "2023-12-29T04:33:33.078661Z",
            "slug": "ghg-accounting-training",
            "title": "GHG Accounting Training",
            "account": null,
            "has_certificate": true,
            "results": [
                {
                    "rank": 1,
                    "content": "text-content",
                    "min_viewing_duration": "00:00:10"
                },
                {
                    "rank": 2,
                    "content": "survey-event",
                    "min_viewing_duration": "00:00:20"
                }
            ]
        }
    """
    serializer_class = SequenceSerializer
    lookup_field = 'slug'
    lookup_url_kwarg = SequenceMixin.sequence_url_kwarg

    def get_object(self):
        return self.sequence

    def delete(self, request, *args, **kwargs):
        """
        Deletes a sequence

        **Tags**: editors

        **Examples**

        .. code-block:: http

            DELETE /api/editables/alliance/sequences/ghg-accounting-training\
 HTTP/1.1

        """
        return self.destroy(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        """
        Updates a sequence

        **Tags**: editors

        **Examples**

        .. code-block:: http

            PUT /api/editables/alliance/sequences/ghg-accounting-training HTTP/1.1

        .. code-block:: json

            {
                "title": "Updated GHG Accounting Training Title",
                "has_certificate": false,
                "extra": "Additional info"
            }

        responds

        .. code-block:: json

            {
                "created_at": "2023-12-29T04:33:33.078661Z",
                "slug": "ghg-accounting-training",
                "title": "Updated GHG Accounting Training Title",
                "account": null,
                "has_certificate": false,
                "extra": "Additional info",
                "results": []
            }
        """
        #pylint:disable=useless-parent-delegation
        return self.update(request, *args, **kwargs)


class AddElementToSequenceAPIView(AccountMixin, SequenceMixin,
                                  ListCreateAPIView):
    """
    Lists page elements in a sequence

    **Tags**: editors

    **Example

    .. code-block:: http

        GET /api/editables/alliance/sequences/ghg-accounting-training/elements HTTP/1.1

    .. code-block:: json

        {
            "previous": null,
            "next": null,
            "count": 2,
            "results": [
                {
                    "rank": 1,
                    "content": "text-content",
                    "min_viewing_duration": "00:00:10"
                },
                {
                    "rank": 2,
                    "content": "survey-event",
                    "min_viewing_duration": "00:00:20"
                }
            ]
        }

    responds

    .. code-block:: json

        {
            "detail": "element added"
        }
    """
    serializer_class = EnumeratedElementSerializer

    def get_queryset(self):
        return self.sequence.sequence_enumerated_elements.order_by('rank')

    def post(self, request, *args, **kwargs):
        """
        Inserts a page element in a sequence

        **Tags**: editors

        **Example

        .. code-block:: http

            POST /api/editables/alliance/sequences/ghg-accounting-training/elements HTTP/1.1

        .. code-block:: json

                {
                    "content": "production",
                    "rank": 10
                }

        responds

        .. code-block:: json

                {
                    "rank": 1,
                    "content": "text-content",
                    "min_viewing_duration": "00:00:00"
                }
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        is_certificate = serializer.validated_data.pop('certificate', False)
        rank = serializer.validated_data.get('rank')

        if self.sequence.has_certificate:
            last_rank = self.sequence.get_last_element.rank
            if is_certificate:
                return api_response.Response({
                    'detail': 'The sequence already has a certificate.'},
                    status=status.HTTP_400_BAD_REQUEST)
            if rank is not None and rank > last_rank:
                return api_response.Response({
                    'detail': 'Cannot add an element with a rank higher'\
                    ' than the certificate.'},
                    status=status.HTTP_400_BAD_REQUEST)

        try:
            serializer.save(sequence=self.sequence)
            if is_certificate and not self.sequence.has_certificate:
                self.sequence.has_certificate = True
                self.sequence.save()
            serializer = self.get_serializer(serializer.instance)
            headers = self.get_success_headers(serializer.data)
            return api_response.Response(
                serializer.data, status=status.HTTP_201_CREATED,
                headers=headers)
        except IntegrityError as err:
            return api_response.Response(
                {'detail': str(err)},
                status=status.HTTP_400_BAD_REQUEST)

        return api_response.Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST)


class RemoveElementFromSequenceAPIView(AccountMixin, SequenceMixin,
                                       DestroyAPIView):
    """
    Removes a page element from a sequence

    **Tags**: editors

    **Example**

        DELETE /api/editables/alliance/sequences/ghg-accounting-training/elements/1 HTTP/1.1

    responds

        204 No Content
    """
    def get_object(self):
        return get_object_or_404(EnumeratedElements.objects.all(),
            sequence=self.sequence, rank=self.kwargs.get('rank'))

    def perform_destroy(self, instance):
        with transaction.atomic():
            if (self.sequence.has_certificate and
                instance == self.sequence.get_last_element):
                self.sequence.has_certificate = False
                self.sequence.save()
            instance.delete()
