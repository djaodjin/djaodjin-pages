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

import datetime

from deployutils.helpers import datetime_or_now
from django.shortcuts import get_object_or_404
from django.http import Http404
from rest_framework import response as api_response, status
from rest_framework.generics import (DestroyAPIView, ListAPIView, RetrieveAPIView)
from rest_framework.mixins import DestroyModelMixin

from .. import settings
from ..docs import extend_schema
from ..helpers import get_extra, set_extra
from ..mixins import EnumeratedProgressMixin, SequenceProgressMixin, SequenceMixin
from ..models import EnumeratedElements, EnumeratedProgress, LiveEvent
from ..serializers import (EnumeratedProgressSerializer,
        LiveEventAttendeesSerializer)


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
                    not isinstance(elem.viewing_duration, datetime.timedelta)):
                elem.viewing_duration = datetime.timedelta(
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
            time_increment = min(time_elapsed, datetime.timedelta(seconds=settings.PING_INTERVAL+1))
        else:
            # Set the initial increment to the expected ping interval (i.e., 10 seconds)
            time_increment = datetime.timedelta(seconds=settings.PING_INTERVAL)

        instance.viewing_duration += time_increment
        instance.last_ping_time = now
        instance.save()

        serializer = self.get_serializer(instance)
        return api_response.Response(serializer.data, status=status.HTTP_200_OK)


class LiveEventAttendanceAPIView(DestroyModelMixin, EnumeratedProgressRetrieveAPIView):
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
    event_rank_kwarg = 'event_rank'

    serializer_class = EnumeratedProgressSerializer

    def get(self, request, *args, **kwargs):
        # Need to ensure the EnumeratedProgress matches the correct LiveEvent
        # As it currently returns any EnumeratedProgress on the PageElement.
        progress = self.progress
        live_event_rank = get_extra(progress, "live_event_rank")

        if live_event_rank != self.kwargs.get(self.event_rank_kwarg):
            raise Http404

        serializer = self.get_serializer(progress)
        return api_response.Response(
            serializer.data, status=status.HTTP_200_OK)

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
        at_time = datetime_or_now()
        event_rank = kwargs.get(self.event_rank_kwarg)
        progress = self.get_object()
        element = progress.step
        live_event = get_object_or_404(
            LiveEvent, element=element.content, rank=event_rank)

        progress_event_rank = set_extra(
            progress, "live_event_rank", event_rank)

        if progress.viewing_duration < element.min_viewing_duration and live_event.scheduled_at < at_time:
            if progress_event_rank and progress_event_rank != event_rank:
                return api_response.Response(
                    {'detail': f'Attendance already marked for Live Event '
                               f'with rank: {event_rank}'},
                    status=status.HTTP_400_BAD_REQUEST)
            progress.viewing_duration = max(
                progress.viewing_duration, element.min_viewing_duration)
            progress.save()
            serializer = self.get_serializer(progress)
            return api_response.Response(
                serializer.data, status=status.HTTP_201_CREATED)

        return api_response.Response(
            {'detail': 'Attendance not marked'},
            status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, *args, **kwargs):
        '''
        Resets Live Event Attendance
        '''
        # Maybe redundant because we're already resetting EnumeratedProgress
        # in EnumeratedProgressResetAPIView?
        event_rank = kwargs.get(self.event_rank_kwarg)
        progress = self.get_object()

        curr_val = set_extra(
            progress, "live_event_rank", '')

        if curr_val != event_rank:
            return api_response.Response(
                status=status.HTTP_400_BAD_REQUEST)

        progress.viewing_duration = datetime.timedelta(seconds=0)
        progress.save()
        return api_response.Response(status=status.HTTP_204_NO_CONTENT)


class LiveEventAttendeesAPIView(SequenceMixin, ListAPIView):
    serializer_class = LiveEventAttendeesSerializer

    rank_url_kwarg = 'rank'
    event_rank_kwarg = 'event_rank'

    def get_queryset(self):
        element_rank = self.kwargs.get(self.rank_url_kwarg)
        event_rank = self.kwargs.get(self.event_rank_kwarg)

        element = get_object_or_404(
            EnumeratedElements, sequence=self.sequence, rank=element_rank)

        queryset = EnumeratedProgress.objects.filter(
            step__content=element.content,
            viewing_duration__gte=element.min_viewing_duration)

        progress_ids = [progress.id for progress in queryset if
            get_extra(progress, "live_event_rank") == event_rank]
        queryset = queryset.filter(id__in=progress_ids)
        return queryset

    def get(self, request, *args, **kwargs):
        return super(LiveEventAttendeesAPIView, self).get(request, *args, **kwargs)

