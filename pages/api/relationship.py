# Copyright (c) 2017, DjaoDjin inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
# TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import logging

from django.db import transaction
from django.db.models import Max
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.mixins import DestroyModelMixin
from rest_framework.response import Response

from ..mixins import TrailMixin
from ..models import RelationShip
from ..serializers import EdgeCreateSerializer, RelationShipSerializer


LOGGER = logging.getLogger(__name__)


class EdgesUpdateAPIView(TrailMixin, generics.CreateAPIView):

    serializer_class = EdgeCreateSerializer

    def perform_create(self, serializer):
        targets = self.get_full_element_path(self.kwargs.get('path', None))
        sources = self.get_full_element_path(serializer.validated_data.get(
            'source'))
        if len(sources) <= len(targets):
            is_prefix = True
            for source, target in zip(sources, targets[:len(sources)]):
                if source != target:
                    is_prefix = False
                    break
            if is_prefix:
                raise ValidationError({"details": "'%s' cannot be attached"\
                    " under '%s' as it is a leading prefix. That would create"\
                    " a loop." % (
                    " > ".join([source.title for source in sources]),
                    " > ".join([target.title for target in targets]))})
        self.perform_change(sources, targets,
            rank=serializer.validated_data.get('rank', None))


class PageElementMoveAPIView(EdgesUpdateAPIView):
    """
    Move an PageElement from one attachement to another.
    """
    queryset = RelationShip.objects.all()

    def perform_change(self, sources, targets, rank=None):
        old_root = sources[-2]
        root = targets[-1]
        LOGGER.debug("update node %s to be under %s with rank=%s",
            sources[-1], root, rank)
        with transaction.atomic():
            edge = RelationShip.objects.get(
                orig_element=old_root, dest_element=sources[-1])
            if rank is None:
                rank = self.get_queryset().filter(
                    orig_element=root).aggregate(Max('rank')).get(
                    'rank__max', None)
                rank = 0 if rank is None else rank + 1
            else:
                RelationShip.objects.insert_available_rank(root, pos=rank,
                    node=sources[-1] if root == old_root else None)
            if root != old_root:
                edge.orig_element = root
            edge.rank = rank
            edge.save()


class RelationShipListAPIView(DestroyModelMixin, generics.ListCreateAPIView):

    model = RelationShip
    serializer_class = RelationShipSerializer
    queryset = RelationShip.objects.all()

    def delete(self, request, *args, **kwargs):#pylint: disable=unused-argument
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid()
        elements = self.queryset.filter(
            orig_element__slug__in=serializer.validated_data['orig_elements'],
            dest_element__slug__in=serializer.validated_data['dest_elements'])
        elements.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
