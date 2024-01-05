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
                          EnumeratedElements, LiveEvent)
from django.shortcuts import get_object_or_404
from django.views.generic.detail import DetailView

from ..compat import reverse
from ..helpers import update_context_urls
from .. import settings

LOGGER = logging.getLogger(__name__)


class SequenceProgressView(TemplateView):
    template_name = 'pages/app/sequences/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sequence_slug = self.kwargs.get('sequence')
        user = self.request.user
        sequence = get_object_or_404(Sequence, slug=sequence_slug)

        elements = sequence.sequence_enumerated_elements.all().order_by('rank')
        last_element_rank = elements.last().rank if elements else None

        for element in elements:
            element.title = element.page_element.title
            element.url = reverse(
                'sequence_page_element_view',
                args=(sequence.slug, element.rank))
            
            element.is_live_event = LiveEvent.objects.filter(element=element.page_element).exists()
            if sequence.has_certificate:
                element.is_certificate = (element.rank == last_element_rank)

        context.update({
            'user': user,
            'sequence': sequence,
            'elements': elements,
        })

        context_urls = {
            'api_enumerated_progress_user_list': reverse(
                'api_enumerated_progress_user_list', args=(sequence.slug, user.username)),
        }

        if sequence.has_certificate:
            context_urls['certificate_download'] = reverse(
                'certificate_download', args=(sequence.slug,))

        update_context_urls(context, context_urls)

        return context


class SequencePageElementView(DetailView):
    template_name = 'pages/app/sequences/pageelement.html'
    context_object_name = 'element'

    def get_object(self, queryset=None):
        sequence_slug = self.kwargs.get('sequence')
        rank = self.kwargs.get('rank')
        sequence = get_object_or_404(Sequence, slug=sequence_slug)
        element = get_object_or_404(EnumeratedElements, sequence=sequence, rank=rank)

        element.is_live_event = LiveEvent.objects.filter(element=element.page_element).exists()
        if sequence.has_certificate:
            last_element_rank = sequence.sequence_enumerated_elements.order_by('rank').last().rank
            element.is_certificate = element.rank == last_element_rank

        return element

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sequence = self.object.sequence
        user = self.request.user

        previous_element = EnumeratedElements.objects.filter(
            sequence=sequence, rank__lt=self.object.rank).order_by('-rank').first()
        next_element = EnumeratedElements.objects.filter(
            sequence=sequence, rank__gt=self.object.rank).order_by('rank').first()

        if previous_element:
            previous_element.url = reverse('sequence_page_element_view',
                                           args=(sequence.slug, previous_element.rank))
        if next_element:
            next_element.url = reverse('sequence_page_element_view',
                                       args=(sequence.slug, next_element.rank))

        progress = None
        viewing_duration_seconds = 0
        try:
            sequence_progress = SequenceProgress.objects.get(
                sequence=sequence, user=user)
            progress = EnumeratedProgress.objects.get(
                progress=sequence_progress, rank=self.object.rank)
            viewing_duration_seconds = progress.viewing_duration.total_seconds() \
                if progress.viewing_duration else 0
        except (SequenceProgress.DoesNotExist, EnumeratedProgress.DoesNotExist):
            pass

        context.update({
            'sequence': sequence,
            'previous_element': previous_element,
            'next_element': next_element,
            'ping_interval': settings.PING_INTERVAL,
            'progress': progress,
            'viewing_duration_seconds': viewing_duration_seconds,
        })

        context_urls = {
            'api_enumerated_progress_list_create': reverse(
                'api_enumerated_progress_list_create',
                args=(sequence.slug,)),
            'api_enumerated_progress_user_detail': reverse(
                'api_enumerated_progress_user_detail',
                args=(sequence.slug, user.username, self.object.rank)),
            'sequence_progress_view': reverse(
                'sequence_progress_view',
                args=(sequence.slug,)),
        }

        if self.object.is_live_event:
            event = self.object.page_element.events.first()
            if event:
                context_urls['live_event_location'] = event.location

        if self.object.is_certificate:
            certificate = sequence.get_certificate
            if certificate:
                context_urls['certificate_download'] = reverse(
                    'certificate_download',
                    args=(sequence.slug,))

        update_context_urls(context, context_urls)

        return context
