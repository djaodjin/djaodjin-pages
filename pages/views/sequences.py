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

from django.views.generic import TemplateView
from pages.models import (Sequence, SequenceProgress, EnumeratedProgress,
                          EnumeratedElements)
from django.shortcuts import get_object_or_404

from ..compat import reverse
from ..helpers import update_context_urls
from ..mixins import SequenceProgressMixin
from .. import settings

LOGGER = logging.getLogger(__name__)


class SequenceProgressView(SequenceProgressMixin, TemplateView):
    template_name = 'pages/app/sequences/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sequence_slug = self.kwargs.get('sequence')
        user = self.request.user
        self.sequence = get_object_or_404(Sequence, slug=sequence_slug)
        
        queryset = self.get_queryset()
        decorated_queryset = self.decorate_queryset(queryset)

        context.update({
            'user': user,
            'sequence': self.sequence,
            'elements': decorated_queryset,
        })

        context_urls = {
            'api_enumerated_progress_user_list': reverse(
                'api_enumerated_progress_user_list', 
                args=(self.sequence.slug, user.username)),
        }

        if self.sequence.has_certificate:
            context_urls['certificate_download'] = reverse(
                'certificate_download', 
                args=(self.sequence.slug,))

        update_context_urls(context, context_urls)

        return context


class SequencePageElementView(SequenceProgressMixin, TemplateView):
    template_name = 'pages/app/sequences/pageelement.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sequence_slug = self.kwargs.get('sequence')
        self.rank = self.kwargs.get('rank')
        self.sequence = get_object_or_404(Sequence, slug=sequence_slug)

        queryset = self.get_queryset()
        decorated_queryset = self.decorate_queryset(queryset)
        decorated_elements = list(decorated_queryset)
        element = decorated_elements[0] if decorated_elements else None

        previous_element = EnumeratedElements.objects.filter(
            sequence=self.sequence, rank__lt=element.rank).order_by('-rank').first()
        next_element = EnumeratedElements.objects.filter(
            sequence=self.sequence, rank__gt=element.rank).order_by('rank').first()

        if previous_element:
            previous_element.url = reverse(
                'sequence_page_element_view',
                args=(self.sequence.slug, previous_element.rank))
        if next_element:
            next_element.url = reverse(
                'sequence_page_element_view',
                args=(self.sequence.slug, next_element.rank))
        progress = None
        viewing_duration_seconds = 0
        user = self.request.user
        try:
            sequence_progress = SequenceProgress.objects.get(
                sequence=self.sequence, user=user)
            progress = EnumeratedProgress.objects.get(
                progress=sequence_progress, rank=element.rank)
            viewing_duration_seconds = progress.viewing_duration.total_seconds() \
                if progress.viewing_duration else 0
        except (SequenceProgress.DoesNotExist, EnumeratedProgress.DoesNotExist):
            pass

        context.update({
            'sequence': self.sequence,
            'element': element,
            'previous_element': previous_element,
            'next_element': next_element,
            'ping_interval': settings.PING_INTERVAL,
            'progress': progress,
            'viewing_duration_seconds': viewing_duration_seconds,
        })

        context_urls = {
            'api_enumerated_progress_list_create': reverse(
                'api_enumerated_progress_list_create',
                args=(self.sequence.slug,)),
            'api_enumerated_progress_user_detail': reverse(
                'api_enumerated_progress_user_detail',
                args=(self.sequence.slug, user.username, element.rank)),
            'sequence_progress_view': reverse(
                'sequence_progress_view',
                args=(self.sequence.slug,)),
        }

        if hasattr(element, 'is_live_event') and element.is_live_event:
            event = element.page_element.events.first()
            if event:
                context_urls['live_event_location'] = event.location

        if hasattr(element, 'is_certificate') and element.is_certificate:
            certificate = self.sequence.get_certificate
            if certificate:
                context_urls['certificate_download'] = reverse(
                    'certificate_download',
                    args=(self.sequence.slug,))

        update_context_urls(context, context_urls)

        return context
