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
from django.shortcuts import get_object_or_404

from rest_framework import (response as api_response,
                            viewsets, status)
from rest_framework.decorators import action

from ..models import (EnumeratedProgress)
from ..serializers import (EnumeratedProgressSerializer,
                           EnumeratedProgressCreateSerializer,
                           EnumeratedProgressPingSerializer)
from .. import settings


class EnumeratedProgressAPIView(viewsets.ModelViewSet):
    """
    Manages instances of EnumeratedProgress

    This API endpoint allow operations on EnumeratedProgress instances,
    which represent a user's progression within sequences. Each instance holds
    information about the user's progress in a sequence, identified by sequence slug,
    username, and the rank of the specific PageElement within the sequence.

    This endpoint supports listing all progress instances, creating new ones, retrieving
    specific instances, updating, and deleting them.

    Also allows updating the viewing duration of progress instances using
    POST requests on individual instances.

     **Tags**: progress
    """
    queryset = EnumeratedProgress.objects.all().order_by('rank')

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return EnumeratedProgressCreateSerializer
        return EnumeratedProgressSerializer

    def get_queryset(self):
        """
        Retrieve a queryset of EnumeratedProgress instances.
        Can be filtered by sequence_slug and username.
        """
        sequence_slug = self.kwargs.get('sequence')
        username = self.kwargs.get('username')
        queryset = self.queryset

        if sequence_slug:
            queryset = queryset.filter(
                progress__sequence__slug=sequence_slug)
        if username:
            queryset = queryset.filter(
                progress__user__username=username)

        return queryset.order_by('rank')

    def get_object(self):
        """
        Retrieve a specific EnumeratedProgress instance using
        sequence_slug, username, and rank.
        """
        queryset = self.get_queryset()
        rank = self.kwargs.get('rank')

        obj = get_object_or_404(queryset,
                                rank=rank)
        self.check_object_permissions(self.request, obj)
        return obj

    def list(self, request, *args, **kwargs):
        """
        List all EnumeratedProgress instances.

        Accessed via URL:
        - /progress/{sequence} for a specific sequence.
        - /progress/{sequence}/{username} for a specific
        user within a sequence.

        .. code-block:: http

            GET /api/progress/sequence1 HTTP/1.1

        responds

        .. code-block:: json

            "count": 1,
            "next": null,
            "previous": null,
            "results": [
                {
                    "created_at": "2023-11-10T09:42:22.563891Z",
                    "rank": 3,
                    "viewing_duration": "00:00:30"
                }
            ]

        """
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a specific EnumeratedProgress instance.

        Accessed via URL: /progress/{sequence}/{username}/{rank}

        .. code-block:: http

            GET /api/progress/sequence1/user1/3 HTTP/1.1

        responds

        .. code-block:: json

            {
                "sequence_slug": "sequence1",
                "rank": 3,
                "viewing_duration": "00:00:30"
            }
        """
        return super().retrieve(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """
        Delete an EnumeratedProgress instance.

        Accessed via URL: /progress/{sequence}/{username}/{rank}

        .. code-block:: http

            DELETE /api/progress/sequence1/user1/3 HTTP/1.1

        responds with a `204 No Content` status, indicating successful deletion.
        """
        return super().destroy(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        """
        Update an EnumeratedProgress instance.

        Accessed via URL: /progress/{sequence}/{username}/{rank}

        .. code-block:: http

            PATCH /api/progress/sequence1/user1/3 HTTP/1.1

            {
                "viewing_duration": "00:01:00"
            }

        responds

        .. code-block:: json

            {
                "sequence_slug": "sequence1",
                "rank": 3,
                "viewing_duration": "00:01:00"
            }
        """
        return super().update(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    def ping(self, request, *args, **kwargs):
        """
        Update the viewing duration of an EnumeratedProgress instance.

        This endpoint is used to send 'pings' via POST requests to update the
        viewing duration of the progress instance. It prevents too frequent updates
        by checking the time since the last ping.

        .. code-block:: http

            POST /api/progress/sequence1/user1/3 HTTP/1.1

        responds

        .. code-block:: json

            {
                "sequence_slug": "sequence1",
                "username": "user1",
                "rank": 3,
                "viewing_duration": "00:00:40",
                "last_ping_time": "2023-11-13T04:56:04.075172Z"
            }

        """
        return self._handle_ping_viewing(request, *args, **kwargs)

    def _handle_ping_viewing(self, request, *args, **kwargs):
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
