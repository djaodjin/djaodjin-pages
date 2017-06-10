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
from rest_framework.mixins import DestroyModelMixin
from rest_framework import generics
from rest_framework import status
from rest_framework.response import Response

from ..models import PageElement, RelationShip
from ..serializers import EdgeCreateSerializer, RelationShipSerializer


LOGGER = logging.getLogger(__name__)


class EdgesUpdateAPIView(generics.CreateAPIView):

    serializer_class = EdgeCreateSerializer

    def _scan_candidates(self, root, name):
        if root is None:
            candidates = PageElement.objects.get_roots()
        else:
            candidates = root.relationships.all()
        for candidate in candidates:
            if candidate.slug == name:
                return [candidate]
        for candidate in candidates:
            suffix = self._scan_candidates(candidate, name)
            if len(suffix) > 0:
                return [candidate] + suffix
        return []

    def _full_element_path(self, path):
        parts = path.split('/')
        if not parts[0]:
            parts.pop(0)
        results = []
        if len(parts) > 0:
            results = self._scan_candidates(None, parts[0])
            for name in parts[1:]:
                results += self._scan_candidates(results[-1], name)
        return results

    def perform_create(self, serializer):
        targets = self._full_element_path(self.kwargs.get('path', None))
        sources = self._full_element_path(
            serializer.validated_data.get('source'))
        self.perform_change(sources, targets,
            rank=serializer.validated_data.get('rank', None))


class PageElementMoveAPIView(EdgesUpdateAPIView):
    """
    Move an PageElement from one attachement to another.
    """
    queryset = RelationShip.objects.all()

    def perform_change(self, sources, targets, rank=None):
        node = sources[-2]
        root = targets[-1]
        LOGGER.debug("update node %s under %s with rank=%s", node, root, rank)
        with transaction.atomic():
            if rank is None:
                rank = self.get_queryset().filter(
                    orig_element=root).aggregate(Max('rank')).get(
                    'rank__max', None)
                rank = 0 if rank is None else rank + 1
            else:
                RelationShip.objects.insert_available_rank(root, pos=rank)
            edge = RelationShip.objects.get(
                orig_element=node, dest_element=sources[-1])
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
