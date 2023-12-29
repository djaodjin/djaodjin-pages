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

from datetime import timedelta

from django.utils import timezone

from rest_framework import response as api_response, status
from rest_framework.generics import (ListCreateAPIView,
    RetrieveDestroyAPIView)

from ..models import EnumeratedProgress
from ..serializers import (EnumeratedProgressSerializer,
    EnumeratedProgressCreateSerializer, EnumeratedProgressPingSerializer)
from .. import settings


class EnumeratedProgressListCreateAPIView(ListCreateAPIView):

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return EnumeratedProgressCreateSerializer
        return EnumeratedProgressSerializer

    def get_queryset(self):
        sequence = self.kwargs.get('sequence')
        username = self.kwargs.get('username')
        queryset = EnumeratedProgress.objects.filter(
            progress__sequence__slug=sequence).order_by('rank')
        if username:
            queryset = queryset.filter(progress__user__username=username)
        return queryset

    def get(self, request, *args, **kwargs):
        """
        Lists EnumeratedProgress for a Sequence or a user within a Sequence

        **Tags**: Progress

        **Example**

        .. code-block:: http

             GET /api/progress/educational-sequence/alice HTTP/1.1

        responds

        .. code-block:: json

            {
              "count": 1,
              "next": null,
              "previous": null,
              "results": [
                {
                  "created_at": "2020-09-28T00:00:00.0000Z",
                  "rank": 1,
                  "viewing_duration": "00:00:00"
                }
              ]
            }
        """
        return super(EnumeratedProgressListCreateAPIView, self).list(
            request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """
        Creates an EnumeratedProgress for a user on a Sequence

        **Examples**

        .. code-block:: http

            POST /api/progress/educational-sequence HTTP/1.1

        .. code-block:: json

            {
                "sequence_slug": "educational-sequence",
                "username": "alice",
                "rank": 2,
                "viewing_duration": null,
            }

        responds

        .. code-block:: json

            {
                "sequence_slug": "educational-sequence",
                "username": "alice",
                "rank": 2,
                "viewing_duration": "00:00:00"
            }
        """
        return super(EnumeratedProgressListCreateAPIView, self).create(
            request, *args, **kwargs)


class EnumeratedProgressRetrieveDestroyAPIView(RetrieveDestroyAPIView):

    serializer_class = EnumeratedProgressSerializer
    lookup_url_kwarg = 'rank'
    lookup_field = 'rank'

    def get_queryset(self):
        sequence = self.kwargs.get('sequence')
        username = self.kwargs.get('username')
        return EnumeratedProgress.objects.filter(
            progress__user__username=username,
            progress__sequence__slug=sequence)

    def get(self, request, *args, **kwargs):
        """
        Retrieves an EnumeratedProgress instance.

        **Tags**: Progress

        **Examples**

        .. code-block:: http

            GET /api/progress/educational-sequence/alice/1 HTTP/1.1

        responds

        .. code-block:: json

            {
                "created_at": "2020-09-28T00:00:00.0000Z",
                "rank": 1,
                "viewing_duration": "00:00:00"
            }
        """
        return super(EnumeratedProgressRetrieveDestroyAPIView, self).retrieve(
            request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        """
        Deletes a specific EnumeratedProgress instance.

        **Tags**: Progress

        **Examples**

        .. code-block:: http

            DELETE /api/progress/educational-sequence/alice/1 HTTP/1.1

        """
        return super(EnumeratedProgressRetrieveDestroyAPIView, self).destroy(
            request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """
        Updates the viewing duration of a EnumeratedProgress instance.

        **Tags**: Progress, Viewing Durattion

        **Examples**

        .. code-block:: http

            POST /api/progress/educational-sequence/alice/1 HTTP/1.1

        responds

        .. code-block:: json

            {
                "created_at": "2020-09-28T00:00:00.0000Z",
                "rank": 1,
                "viewing_duration": "00:00:56.000000",
                "last_ping_time": "2020-09-28T00:10:00.0000Z"
            }
        """

        instance = self.get_object()
        now = timezone.now()

        if instance.last_ping_time:
            time_elapsed = now - instance.last_ping_time
            # Add only the actual time elapsed, with a cap for inactivity
            time_increment = min(time_elapsed, timedelta(seconds=settings.PING_INTERVAL+1))
        else:
            # Set the initial increment to the expected ping interval (i.e., 10 seconds)
            time_increment = timedelta(seconds=settings.PING_INTERVAL)

        instance.viewing_duration += time_increment
        instance.last_ping_time = now
        instance.save()

        status_code = status.HTTP_200_OK
        serializer = EnumeratedProgressPingSerializer(instance)
        return api_response.Response(serializer.data, status=status_code)
