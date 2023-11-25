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
from django.shortcuts import get_object_or_404
from rest_framework import (response as api_response,
                            viewsets, status)
from rest_framework.decorators import action
from rest_framework.views import APIView

from ..models import (Sequence, EnumeratedElements,
   SequenceProgress, EnumeratedProgress, LiveEvent)
from ..serializers import (SequenceSerializer,
   EnumeratedElementSerializer, AttendanceInputSerializer)

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
                return api_response.Response(
                    {'detail': 'element removed'}, status=status.HTTP_200_OK)
            except EnumeratedElements.DoesNotExist:
                return api_response.Response({'detail': 'element not found in sequence'},
                                             status=status.HTTP_404_NOT_FOUND)
        return api_response.Response({'detail': 'Invalid rank'}, status=status.HTTP_400_BAD_REQUEST)


class LiveEventAttendanceAPIView(APIView):
    '''
    Manages attendance tracking for live events

    This API endpoint allows for marking attendance at live events,
    represented by the LiveEvent model. It accepts URL parameters to identify
    the specific live event and the user attending, and updates the EnumeratedProgress
    instance associated with the event and user to reflect their attendance.

    The relevant user's EnumeratedProgress viewing duration for the event is updated to
    meet the minimum viewing duration requirement of the associated EnumeratedElement.

    **Tags**: attendance, live events
    '''
    def post(self, request, *args, **kwargs):
        """
        - **Mark a User's attendance at a Live Event**

        .. code-block:: http

            POST /api/sequences/{sequence_slug}/{rank}/events/{username}/mark-attendance HTTP/1.1

        URL Parameters:
            - sequence_slug (str): The slug of the sequence associated with the live event.
            - username (str): The username of the user attending the live event.
            - rank (int): The rank of the enumerated element in the sequence.

        Responds with a status indicating whether the attendance was successfully marked or not.

        On successful attendance marking:

        .. code-block:: json

            {
                "detail": "Attendance marked successfully"
            }

        On failure to mark attendance (e.g., invalid parameters, event not found):

        .. code-block:: json

            {
                "detail": "Attendance not marked"
            }

        """

        input_serializer = AttendanceInputSerializer(data=self.kwargs)
        if not input_serializer.is_valid():
            return api_response.Response(
                input_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        sequence = input_serializer.validated_data['sequence']
        user = input_serializer.validated_data['username']
        rank = input_serializer.validated_data['rank']

        sequence_progress = get_object_or_404(
            SequenceProgress, user=user, sequence=sequence)
        enumerated_progress = get_object_or_404(
            EnumeratedProgress, progress=sequence_progress, rank=rank)
        enumerated_element = get_object_or_404(
            EnumeratedElements, rank=rank, sequence=sequence)
        page_element = enumerated_element.page_element
        live_event = get_object_or_404(
            LiveEvent, sequence=sequence, element=page_element)

        if page_element.events.first() == live_event and \
           enumerated_progress.viewing_duration < enumerated_element.min_viewing_duration:
            enumerated_progress.viewing_duration = enumerated_element.min_viewing_duration
            enumerated_progress.save()
            return api_response.Response(
                {'detail': 'Attendance marked successfully'}, status=status.HTTP_200_OK)
        return api_response.Response(
            {'detail': 'Attendance not marked'}, status=status.HTTP_400_BAD_REQUEST)
