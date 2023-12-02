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

from django.db import IntegrityError
from rest_framework import (response as api_response,
                            viewsets, status)
from rest_framework.decorators import action

from ..models import (Sequence, EnumeratedElements)
from ..serializers import (SequenceSerializer, EnumeratedElementSerializer)

LOGGER = logging.getLogger(__name__)

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
    queryset = Sequence.objects.all().order_by('slug')
    lookup_field = 'slug'

    serializer_action_classes = {
        'add_element': EnumeratedElementSerializer,
        'remove_element': EnumeratedElementSerializer,
        'create': SequenceSerializer,
        'update': SequenceSerializer
    }

    def get_serializer_class(self):
        return self.serializer_action_classes.get(
            self.action, super().get_serializer_class())

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

    @action(detail=True, methods=['post'], url_path='elements')
    def add_element(self, request, slug=None):
        """
        - **Add Element to Sequence**

        Adds an element to a sequence. Creates a new `EnumeratedElements` instance.
        .. code-block:: http

            POST /api/sequences/sequence1/elements HTTP/1.1
            Content-Type: application/json

            {
                "page_element": "production",
                "rank": 1
            }

        responds

        .. code-block:: json

            {
                "detail": "element added"
            }
            """
        sequence = self.get_object()
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            try:
                serializer.save(sequence=sequence)
                return api_response.Response(
                    {'detail': 'element added'}, status=status.HTTP_201_CREATED)
            except IntegrityError:
                return api_response.Response(
                    {'detail':
                         'An element already exists at this rank for this sequence.'},
                          status=status.HTTP_400_BAD_REQUEST)
        return api_response.Response(
            {'detail': 'invalid parameters'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'], url_path='elements/(?P<element_rank>\\d+)')
    def remove_element(self, request, slug=None, element_rank=None):
        """
        - **Remove Element from Sequence**

        Removes an element from a sequence by its rank.

        .. code-block:: http

            DELETE /api/sequences/sequence1/elements/1 HTTP/1.1
            Content-Type: application/json

        responds

        .. code-block:: json

            {
                "detail": "element removed"
            }
        """
        sequence = self.get_object()
        if element_rank is not None:
            try:
                element = EnumeratedElements.objects.get(sequence=sequence, rank=element_rank)
                element.delete()
                return api_response.Response({'detail': 'element removed'}, status=status.HTTP_200_OK)
            except EnumeratedElements.DoesNotExist:
                return api_response.Response({'detail': 'element not found in sequence'},
                                             status=status.HTTP_404_NOT_FOUND)
        return api_response.Response({'detail': 'Invalid rank'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['patch'], url_path='certificate')
    def add_certificate(self, request, slug=None):
        """
        - **Add a Certificate to Sequence**

        Sets the Sequence's has_certificate field to True, enabling Certificates
        for users that complete the Sequence.

        .. code-block:: http

            PATCH /api/sequences/sequence1/certificate HTTP/1.1
            Content-Type: application/json

        responds

        .. code-block:: json

            {
                "detail": "certificate added"
            }
            """
        sequence = self.get_object()
        if not sequence.has_certificate:
            sequence.has_certificate = True
            sequence.save()
            return api_response.Response(
           {'detail': 'certificate added'},
                status=status.HTTP_200_OK)
        return api_response.Response(
            {'detail': 'a certificate already exists'},
            status=status.HTTP_400_BAD_REQUEST)

