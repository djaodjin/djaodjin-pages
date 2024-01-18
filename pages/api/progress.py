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

from datetime import timedelta

from deployutils.helpers import datetime_or_now
from rest_framework import response as api_response, status
from rest_framework.generics import DestroyAPIView, ListAPIView, RetrieveAPIView

from .. import settings
from ..docs import extend_schema
from ..mixins import EnumeratedProgressMixin, SequenceProgressMixin
from ..models import EnumeratedElements, EnumeratedProgress, LiveEvent
from ..serializers import (EnumeratedProgressSerializer,
    AttendanceInputSerializer)


class EnumeratedProgressListAPIView(SequenceProgressMixin, ListAPIView):
    """
    Lists progress for a user on a sequence

    **Tags**: content, progress

    **Example**

    .. code-block:: http

         GET /api/progress/steve/ghg-accounting-training HTTP/1.1

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
    serializer_class = EnumeratedProgressSerializer

    def get_queryset(self):
        # Implementation Note:
        # Couldn't figure out how to return all EnumeratedElements for
        # a sequence annotated with the viewing_duration for a specific user.
        queryset = EnumeratedElements.objects.raw(
"""
WITH progresses AS (
SELECT * FROM pages_enumeratedprogress
INNER JOIN pages_sequenceprogress
ON pages_enumeratedprogress.sequence_progress_id = pages_sequenceprogress.id
WHERE pages_sequenceprogress.user_id = %(user_id)d
)
SELECT *
FROM pages_enumeratedelements
LEFT OUTER JOIN progresses
ON pages_enumeratedelements.id = progresses.step_id
WHERE pages_enumeratedelements.sequence_id = %(sequence_id)d
""" % {
    'user_id': self.user.pk,
    'sequence_id': self.sequence.pk
})
        return queryset

    def paginate_queryset(self, queryset):
        try:
            page = super(
                EnumeratedProgressListAPIView, self).paginate_queryset(queryset)
        except TypeError:
            # Python2.7/Django1.11 doesn't support `len` on `RawQuerySet`.
            page = super(EnumeratedProgressListAPIView, self).paginate_queryset(
                list(queryset))
        results = page if page else queryset
        for elem in results:
            if (elem.viewing_duration is not None and
                not isinstance(elem.viewing_duration, timedelta)):
                elem.viewing_duration = timedelta(
                    microseconds=elem.viewing_duration)
        return results


class EnumeratedProgressResetAPIView(SequenceProgressMixin, DestroyAPIView):
    """
    Resets a user's progress on a sequence

    **Tags**: editors, progress

    **Example**

    .. code-block:: http

         DELETE /api/attendance/alliance/ghg-accounting-training/steve HTTP/1.1

    responds

         204 No Content
    """
    def delete(self, request, *args, **kwargs):
        EnumeratedProgress.objects.filter(
            sequence_progress__user=self.user,
            step__sequence=self.sequence).delete()
        return api_response.Response(status=status.HTTP_204_NO_CONTENT)


class EnumeratedProgressRetrieveAPIView(EnumeratedProgressMixin,
                                        RetrieveAPIView):
    """
    Retrieves viewing time for an element

    **Tags**: content, progress

    **Examples**

    .. code-block:: http

        GET /api/progress/steve/ghg-accounting-training/1 HTTP/1.1

    responds

    .. code-block:: json

        {
            "created_at": "2020-09-28T00:00:00.0000Z",
            "rank": 1,
            "viewing_duration": "00:00:00"
        }
    """
    serializer_class = EnumeratedProgressSerializer

    def get_object(self):
        return self.progress

    @extend_schema(request=None)
    def post(self, request, *args, **kwargs):
        """
        Updates viewing time for an element

        **Tags**: content, progress

        **Examples**

        .. code-block:: http

            POST /api/progress/steve/ghg-accounting-training/1 HTTP/1.1

        responds

        .. code-block:: json

            {
                "rank": 1,
                "created_at": "2020-09-28T00:00:00.0000Z",
                "viewing_duration": "00:00:56.000000"
            }
        """
        instance = self.get_object()
        now = datetime_or_now()

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
        serializer = self.get_serializer(instance)
        return api_response.Response(serializer.data, status=status_code)


class LiveEventAttendanceAPIView(EnumeratedProgressRetrieveAPIView):
    """
    Retrieves attendance to live event

    **Tags**: content, progress

    **Examples**

    .. code-block:: http

        GET /api/attendance/alliance/ghg-accounting-training/1/steve HTTP/1.1

    responds

    .. code-block:: json

        {
            "created_at": "2020-09-28T00:00:00.0000Z",
            "rank": 1,
            "viewing_duration": "00:00:00"
        }
    """
    rank_url_kwarg = 'rank'

    def get_serializer_class(self):
        if self.request.method.lower() == 'post':
            return AttendanceInputSerializer
        return super(LiveEventAttendanceAPIView, self).get_serializer_class()

    def post(self, request, *args, **kwargs):
        """
        Marks a user's attendance to a live event

        Indicates that a user attended a live event, hence fullfilling
        the requirements for the element of the sequence.

        **Tags**: editors, live-events, attendance

        **Example**

        .. code-block:: http

            POST /api/attendance/alliance/ghg-accounting-training/1/steve HTTP/1.1

        responds

        .. code-block:: json

            {
                "detail": "Attendance marked successfully"
            }
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        progress = self.get_object()
        element = progress.step
        live_event = LiveEvent.objects.filter(element=element.content).first()

        # We use if live_event to confirm the existence of the LiveEvent object
        if (live_event and
            progress.viewing_duration <= element.min_viewing_duration):
            progress.viewing_duration = element.min_viewing_duration
            progress.save()
            return api_response.Response(
                {'detail': 'Attendance marked successfully'},
                status=status.HTTP_200_OK)
        return api_response.Response(
            {'detail': 'Attendance not marked'},
            status=status.HTTP_400_BAD_REQUEST)
