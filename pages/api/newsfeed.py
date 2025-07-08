# Copyright (c) 2025, DjaoDjin inc.
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
from __future__ import unicode_literals

from django.db.models import Subquery, OuterRef, F, Q, Count
from rest_framework import generics

from ..mixins import UserMixin
from ..models import Follow, PageElement
from ..serializers import UserNewsSerializer


class NewsFeedListAPIView(UserMixin, generics.ListAPIView):
    """
    Retrieves relevant news for a user

    **Tags**: content, user

    **Examples**

    .. code-block:: http

        GET /api/content/steve/newsfeed HTTP/1.1

    responds

    .. code-block:: json

        {
          "count": 1,
          "next": null,
          "previous": null,
          "results": [{
              "path": "/metal/boxes-and-enclosures/production/\
energy-efficiency/process-heating/combustion/adjust-air-fuel-ratio",
              "text_updated_at": "2024-01-01T00:00:00Z",
              "last_read_at": "2023-12-01T00:00:00Z",
              "nb_comments_since_last_read": 5,
              "descr": ""
          }]
        }
    """
    serializer_class = UserNewsSerializer

    @property
    def visibility(self):
        return None

    @property
    def owners(self):
        return None

    def get_updated_elements(self, start_at=None, ends_at=None):
        """
        Returns `PageElement` accessible to a user, ordered by last update
        time, with a priority with the ones followed.
        """
        queryset = PageElement.objects.filter_available(
            visibility=self.visibility, accounts=self.owners,
            start_at=start_at, ends_at=ends_at).exclude(
            Q(text__isnull=True) | Q(text="")).annotate(
            follow=Count('followers',
                filter=Q(followers__user=self.user)),
            # We cannot use `last_read_at=Max('followers__last_read_at',
            # filter=Q(followers__user=self.user))` here, otherwise Django
            # ORM is not able to create a valid SQL query for
            # `nb_comments_since_last_read`.
            last_read_at=Subquery(
                Follow.objects.filter(
                    user=self.user,
                    element=OuterRef('pk')
                ).values('last_read_at')[:1]),
            nb_comments_since_last_read=Count('comments',
                filter=Q(comments__created_at__gte=F('last_read_at')))
            ).order_by('-follow', '-text_updated_at')
        return queryset


    def get_queryset(self):
        return self.get_updated_elements()
