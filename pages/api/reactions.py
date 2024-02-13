# Copyright (c) 2021, DjaoDjin inc.
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

from deployutils.helpers import datetime_or_now
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Subquery, OuterRef, F, Q
from django.db.models.functions import Coalesce, Greatest
from rest_framework import generics

from .. import signals
from ..compat import is_authenticated
from ..mixins import PageElementMixin, UserMixin
from ..models import Comment, Follow, Vote
from ..serializers import CommentSerializer, PageElementSerializer, PageElementUpdateSerializer


class FollowAPIView(PageElementMixin, generics.CreateAPIView):
    """
    Follows a page element

    The authenticated user making the request will receive notification
    whenever someone comments on the practice.

    **Tags**: content

    **Examples**

    .. code-block:: http

         POST /api/content/follow/adjust-air-fuel-ratio HTTP/1.1

    .. code-block:: json

         {}

    responds

    .. code-block:: json

        {
            "slug": "water-user",
            "title": "How to reduce water usage?"
        }
    """
    serializer_class = PageElementSerializer

    def perform_create(self, serializer):
        if not is_authenticated(self.request):
            raise PermissionDenied()
        Follow.objects.subscribe(self.element, user=self.request.user)
        serializer.instance = self.element


class UnfollowAPIView(PageElementMixin, generics.CreateAPIView):
    """
    Unfollows a page element

    The authenticated user making the request will stop receiving notification
    whenever someone comments on the practice.

    **Tags**: content

    **Examples**

    .. code-block:: http

         POST /api/content/unfollow/adjust-air-fuel-ratio HTTP/1.1

    .. code-block:: json

         {}

    responds

    .. code-block:: json

        {
            "slug": "water-user",
            "title": "How to reduce water usage?"
        }
    """
    serializer_class = PageElementSerializer

    def perform_create(self, serializer):
        if not is_authenticated(self.request):
            raise PermissionDenied()
        Follow.objects.unsubscribe(self.element, user=self.request.user)
        serializer.instance = self.element


class UpvoteAPIView(PageElementMixin, generics.CreateAPIView):
    """
    Upvotes a page element

    The authenticated user making the request indicates the practice is
    considered worthwhile implementing.

    **Tags**: content

    **Examples**

    .. code-block:: http

         POST /api/content/upvote/adjust-air-fuel-ratio HTTP/1.1

    .. code-block:: json

         {}

    responds

    .. code-block:: json

        {
            "slug": "water-user",
            "title": "How to reduce water usage?"
        }
    """
    serializer_class = PageElementSerializer

    def perform_create(self, serializer):
        if not is_authenticated(self.request):
            raise PermissionDenied()
        Vote.objects.vote_up(self.element, user=self.request.user)
        serializer.instance = self.element


class DownvoteAPIView(PageElementMixin, generics.CreateAPIView):
    """
    Downvotes a page element

    The authenticated user making the request indicates the practice is
    not worth implementing.

    **Tags**: content

    **Examples**

    .. code-block:: http

         POST /api/content/downvote/adjust-air-fuel-ratio HTTP/1.1

    .. code-block:: json

         {}

    responds

    .. code-block:: json

        {
            "slug": "water-user",
            "title": "How to reduce water usage?"
        }
    """
    serializer_class = PageElementSerializer

    def perform_create(self, serializer):
        if not is_authenticated(self.request):
            raise PermissionDenied()
        Vote.objects.vote_down(self.element, user=self.request.user)
        serializer.instance = self.element


class CommentListCreateAPIView(PageElementMixin, generics.ListCreateAPIView):

    serializer_class = CommentSerializer

    def get_queryset(self):
        return Comment.objects.filter(
            element=self.element).select_related('user').order_by('created_at')

    def get(self, request, *args, **kwargs):
        """
        Lists comments on a page element

        **Tags**: content

        **Examples**

        .. code-block:: http

             GET /api/content/comments/adjust-air-fuel-ratio HTTP/1.1

        responds

        .. code-block:: json

            {
              "count": 1,
              "next": null,
              "previous": null,
              "results": [
                {
                  "created_at": "2020-09-28T00:00:00.0000Z",
                  "user": "steve",
                  "text": "How long does it take to see improvements?"
                }
              ]
            }
        """
        #pylint:disable=useless-super-delegation
        return super(CommentListCreateAPIView, self).get(
            request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """
        Comments on a page element

        **Tags**: content

        **Examples**

        .. code-block:: http

             POST /api/content/comments/adjust-air-fuel-ratio HTTP/1.1

        .. code-block:: json

            {
                "text": "How long does it take to see improvements?"
            }

        responds

        .. code-block:: json

            {
              "created_at": "2020-09-28T00:00:00.0000Z",
              "user": "steve",
              "text": "How long does it take to see improvements?"
            }
        """
        #pylint:disable=useless-super-delegation
        return super(CommentListCreateAPIView, self).post(
            request, *args, **kwargs)

    def perform_create(self, serializer):
        if not is_authenticated(self.request):
            raise PermissionDenied()

        with transaction.atomic():
            serializer.save(created_at=datetime_or_now(),
                element=self.element, user=self.request.user)
            # Subscribe the commenting user to this element
            Follow.objects.subscribe(self.element, user=self.request.user)

        signals.comment_was_posted.send(
            sender=__name__, comment=serializer.instance, request=self.request)


class NewsFeedListAPIView(UserMixin, generics.ListAPIView):
    serializer_class = PageElementUpdateSerializer

    def get_queryset(self):
        user = self.user

        last_comments_subquery = Comment.objects.filter(
            element=OuterRef('pk'),
        ).order_by('-created_at').values('created_at')[:1]

        queryset = Follow.objects.followed_elements(user).annotate(
            last_comment_time=Subquery(last_comments_subquery),
            last_update_time=Greatest(
                Coalesce('text_updated_at', 'last_comment_time'),
                Coalesce('last_comment_time', 'text_updated_at')),
            # Greatest doesn't work on non-null values
            # So we use Coalesces for both values
            last_read_at=Subquery(
                Follow.objects.filter(
                    user=user, element=OuterRef('pk')
                    ).values('last_read_at')[:1]
                )
            ).exclude(
                Q(last_update_time__isnull=True) |
                Q(last_update_time__lte=F('last_read_at'))
            ).order_by('-last_update_time')

        return queryset

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)
