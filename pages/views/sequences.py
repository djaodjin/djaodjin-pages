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
import logging

from deployutils.helpers import datetime_or_now
from django.core.exceptions import PermissionDenied
from django.views.generic import TemplateView, DetailView
from extended_templates.backends.pdf import PdfTemplateResponse

from .. import settings
from ..compat import reverse
from ..helpers import update_context_urls
from ..mixins import EnumeratedProgressMixin, SequenceProgressMixin
from ..models import EnumeratedElements

LOGGER = logging.getLogger(__name__)


class SequenceProgressView(SequenceProgressMixin, TemplateView):
    template_name = 'pages/app/sequences/index.html'

    def get_context_data(self, **kwargs):
        context = super(SequenceProgressView, self).get_context_data(**kwargs)

        queryset = self.get_queryset()
        decorated_queryset = self.decorate_queryset(queryset)

        context.update({
            'user': self.user,
            'sequence': self.sequence,
            'elements': decorated_queryset,
        })

        context_urls = {
            'api_enumerated_progress_user_list': reverse(
                'api_enumerated_progress_user_list',
                args=(self.user, self.sequence,)),
        }

        if self.sequence.has_certificate:
            context_urls['certificate_download'] = reverse(
                'certificate_download',
                args=(self.user, self.sequence,))

        update_context_urls(context, context_urls)

        return context


class SequencePageElementView(EnumeratedProgressMixin, TemplateView):

    template_name = 'pages/app/sequences/pageelement.html'

    def get_context_data(self, **kwargs):
        #pylint:disable=too-many-locals
        context = super(SequencePageElementView,
            self).get_context_data(**kwargs)

        element = self.progress.step
        previous_element = EnumeratedElements.objects.filter(
            sequence=element.sequence, rank__lt=element.rank).order_by(
            '-rank').first()
        next_element = EnumeratedElements.objects.filter(
            sequence=element.sequence, rank__gt=element.rank).order_by(
            'rank').first()

        if previous_element:
            previous_element.url = reverse(
                'sequence_page_element_view',
                args=(self.user, element.sequence, previous_element.rank))
        if next_element:
            next_element.url = reverse(
                'sequence_page_element_view',
                args=(self.user, element.sequence, next_element.rank))
        viewing_duration_seconds = (
            self.progress.viewing_duration.total_seconds()
            if self.progress.viewing_duration else 0)

        context.update({
            'sequence': element.sequence,
            'element': element,
            'previous_element': previous_element,
            'next_element': next_element,
            'ping_interval': settings.PING_INTERVAL,
            'progress': self.progress,
            'viewing_duration_seconds': viewing_duration_seconds,
        })

        context_urls = {
            'api_enumerated_progress_user_detail': reverse(
                'api_enumerated_progress_user_detail',
                args=(self.user, element.sequence, element.rank)),
            'sequence_progress_view': reverse(
                'sequence_progress_view',
                args=(self.user, element.sequence,)),
        }

        if hasattr(element, 'is_live_event') and element.is_live_event:
            event = element.content.events.first()
            if event:
                context_urls['live_event_location'] = event.location

        if hasattr(element, 'is_certificate') and element.is_certificate:
            certificate = element.sequence.get_certificate
            if certificate:
                context_urls['certificate_download'] = reverse(
                    'certificate_download', args=(element.sequence,))

        update_context_urls(context, context_urls)

        return context


class CertificateDownloadView(SequenceProgressMixin, DetailView):

    template_name = 'pages/certificate.html'
    response_class = PdfTemplateResponse

    def get_context_data(self, **kwargs):
        context = super(CertificateDownloadView, self).get_context_data(
            **kwargs)
        has_completed_sequence = self.sequence_progress.is_completed
        context.update({
            'user': self.user,
            'sequence': self.sequence_progress.sequence,
            'has_certificate': self.sequence_progress.sequence.has_certificate,
            'certificate': self.sequence_progress.sequence.get_certificate,
            'has_completed_sequence': has_completed_sequence
        })

        if has_completed_sequence:
            completion_date = datetime_or_now(
                self.sequence_progress.completion_date)
            if not self.sequence_progress.completion_date:
                self.sequence_progress.completion_date = completion_date
                self.sequence_progress.save()
            context['completion_date'] = completion_date

        return context

    def get(self, request, *args, **kwargs):
        if (self.sequence_progress.has_certificate and
            not self.sequence_progress.is_completed):
            raise PermissionDenied("Certificate is not available for download"\
                " until you complete all elements.")
        return super(CertificateDownloadView, self).get(
            request, *args, **kwargs)
