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
from rest_framework import response as api_response, status
from rest_framework.views import APIView
from rest_framework.generics import (ListCreateAPIView,
    RetrieveUpdateDestroyAPIView)

from ..models import (Sequence, EnumeratedElements, SequenceProgress,
    EnumeratedProgress, LiveEvent)
from ..serializers import (SequenceSerializer, EnumeratedElementSerializer,
    AttendanceInputSerializer)

LOGGER = logging.getLogger(__name__)


class SequenceListCreateAPIView(ListCreateAPIView):
    queryset = Sequence.objects.all().order_by('slug')
    serializer_class = SequenceSerializer

    def get(self, request, *args, **kwargs):
        """
        Lists Sequences

        **Tags**: Sequence

        **Example**

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
                  "created_at": "2020-09-28T00:00:00.0000Z",
                  "slug": "educational-sequence",
                  "title": "Educational Sequence",
                  "account": "djaopsp",
                  "has_certificate": true,
                  "extra": null,
                  "elements": [
                    {
                      "page_element": "text-content",
                      "rank": 1,
                      "min_viewing_duration": "00:00:10"
                    },
                    {
                      "page_element": "survey-event",
                      "rank": 2,
                      "min_viewing_duration": "00:00:20"
                    }
                  ]
                }
              ]
            }
        """
        return super(SequenceListCreateAPIView, self).list(
            request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """
        Creates a Sequence

        **Examples**

        .. code-block:: http

            POST /api/sequences HTTP/1.1

        .. code-block:: json

            {
                "slug": "educational-sequence2",
                "title": "Educational Sequence 2",
                "has_certificate": True,
                "viewing_duration": null,
            }

        responds

        .. code-block:: json

            {
              "created_at": "2023-01-01T04:00:00.000000Z",
              "slug": "educational-sequence2",
              "title": "Educational Sequence 2",
              "account": null,
              "has_certificate": true,
              "extra": null,
              "elements": []
            }
        """
        return super(SequenceListCreateAPIView, self).create(
            request, *args, **kwargs)


class SequenceRetrieveUpdateDestroyAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Sequence.objects.all().order_by('slug')
    serializer_class = SequenceSerializer
    lookup_field = 'slug'
    lookup_url_kwarg = 'sequence'

    def get(self, request, *args, **kwargs):
        """
        Retrieves a Sequence.

        **Tags**: Sequence

        **Examples**

        .. code-block:: http

            GET /api/sequences/educational-sequence2 HTTP/1.1

        responds

        .. code-block:: json

            {
                "created_at": "2023-12-29T04:33:33.078661Z",
                "slug": "educational-sequence2",
                "title": "Educational Sequence 2",
                "account": null,
                "has_certificate": true,
                "extra": null,
                "elements": []
            }
        """
        return super(SequenceRetrieveUpdateDestroyAPIView, self).retrieve(
            request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        """
        Deletes a Sequence.

        **Tags**: Sequence

        **Examples**

        .. code-block:: http

            DELETE /api/progress/educational-sequence HTTP/1.1

        """
        print('deleting')
        return super(SequenceRetrieveUpdateDestroyAPIView, self).destroy(
            request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        """
        Updates a Sequence.

        **Tags**: Sequence

        **Examples**

        .. code-block:: http

            PATCH /api/progress/educational-sequence HTTP/1.1

        .. code-block:: json

            {
                "title": "Updated Educational Sequence Title",
                "has_certificate": false,
                "extra": "Additional info"
            }

        responds

        .. code-block:: json

            {
                "created_at": "2023-12-29T04:33:33.078661Z",
                "slug": "educational-sequence",
                "title": "Updated Educational Sequence Title",
                "account": null,
                "has_certificate": false,
                "extra": "Additional info",
                "elements": []
            }
        """
        return super(SequenceRetrieveUpdateDestroyAPIView, self).partial_update(
            request, *args, **kwargs)


class AddElementToSequenceAPIView(APIView):
    """
    Adds an element to a sequence.

    **Tags**: Sequence

    **Example**

    .. code-block:: http

        POST /api/sequences/educational-sequence/elements HTTP/1.1

    .. code-block:: json

            {
                "page_element": "production",
                "rank": 10
            }

    responds

    .. code-block:: json

        {
            "detail": "element added"
        }
    """

    def post(self, request, *args, **kwargs):
        sequence_slug = self.kwargs.get('sequence')
        sequence = Sequence.objects.get(slug=sequence_slug)
        serializer = EnumeratedElementSerializer(data=request.data)

        if serializer.is_valid(raise_exception=True):
            is_certificate = serializer.validated_data.pop('certificate', False)
            rank = serializer.validated_data.get('rank')

            if sequence.has_certificate:
                last_rank = sequence.sequence_enumerated_elements.order_by('-rank').first().rank
                if is_certificate:
                    return api_response.Response({
                        'detail': 'The sequence already has a certificate.'},
                        status=status.HTTP_400_BAD_REQUEST)
                if rank is not None and rank > last_rank:
                    return api_response.Response({
                        'detail': 'Cannot add an element with a rank higher than the certificate.'},
                        status=status.HTTP_400_BAD_REQUEST)

            try:
                serializer.save(sequence=sequence)
                if is_certificate and not sequence.has_certificate:
                    sequence.has_certificate = True
                    sequence.save()
                return api_response.Response(
                    {'detail': 'Element added'},
                    status=status.HTTP_201_CREATED)
            except IntegrityError as e:
                return api_response.Response(
                    {'detail': str(e)},
                    status=status.HTTP_400_BAD_REQUEST)

        return api_response.Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST)


class RemoveElementFromSequenceAPIView(APIView):
    """
    Removes an element from a sequence by its rank.

    **Example**

        DELETE /api/sequences/educational-sequence/elements/1 HTTP/1.1

    responds

        {
            "detail": "element removed"
        }
    """

    def delete(self, request, *args, **kwargs):
        sequence_slug = self.kwargs.get('sequence')
        rank = self.kwargs.get('rank')
        sequence = Sequence.objects.get(slug=sequence_slug)
        if rank is not None:
            try:
                element = EnumeratedElements.objects.get(sequence=sequence, rank=rank)
                if element.is_certificate:
                    sequence.has_certificate = False
                    sequence.save()
                element.delete()
                return api_response.Response(
                    {'detail': 'element removed'}, status=status.HTTP_200_OK)
            except EnumeratedElements.DoesNotExist:
                return api_response.Response(
                    {'detail': 'element not found in sequence'}, status=status.HTTP_404_NOT_FOUND)

        return api_response.Response({'detail': 'Invalid rank'}, status=status.HTTP_400_BAD_REQUEST)


class LiveEventAttendanceAPIView(APIView):
    '''
    Allows marking a user's attendance to a Live Event.


    **Tags**: attendance, live events
    '''
    def post(self, request, *args, **kwargs):
        """
        Mark a User's attendance at a Live Event

        **Example**

        .. code-block:: http

            POST /api/sequences/{sequence}/{rank}/{username}/mark-attendance HTTP/1.1

        Responds

        .. code-block:: json

            {
                "detail": "Attendance marked successfully"
            }
        """

        input_serializer = AttendanceInputSerializer(data=self.kwargs)
        input_serializer.is_valid(raise_exception=True)

        sequence = input_serializer.validated_data['sequence']
        user = input_serializer.validated_data['username']
        rank = input_serializer.validated_data['rank']

        sequence_progress, _ = SequenceProgress.objects.get_or_create(
            user=user, sequence=sequence)
        enumerated_progress, _ = EnumeratedProgress.objects.get_or_create(
            progress=sequence_progress, rank=rank)
        enumerated_element = EnumeratedElements.objects.get(
            rank=rank, sequence=sequence)
        page_element = enumerated_element.page_element
        live_event = LiveEvent.objects.filter(element=page_element).first()

        # We use if live_event to confirm the existence of the LiveEvent object
        if live_event and enumerated_progress.viewing_duration <= enumerated_element.min_viewing_duration:
            enumerated_progress.viewing_duration = enumerated_element.min_viewing_duration
            enumerated_progress.save()
            return api_response.Response(
                {'detail': 'Attendance marked successfully'}, status=status.HTTP_200_OK)
        return api_response.Response(
            {'detail': 'Attendance not marked'}, status=status.HTTP_400_BAD_REQUEST)
