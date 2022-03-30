# Copyright (c) 2021, Djaodjin Inc.
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

from django.http import Http404
from django.views.generic import TemplateView
from deployutils.apps.django.mixins import AccessiblesMixin

from ..compat import NoReverseMatch, reverse, six
from ..models import RelationShip
from ..mixins import AccountMixin, TrailMixin
from ..utils import update_context_urls


LOGGER = logging.getLogger(__name__)


class PageElementEditableView(TrailMixin, AccountMixin, AccessiblesMixin,
                              TemplateView):

    template_name = 'pages/index.html'

    @property
    def is_prefix(self):
        if not hasattr(self, '_is_prefix'):
            try:
                self._is_prefix = (not self.element or
                    RelationShip.objects.filter(
                        orig_element=self.element).exists())
            except Http404:
                self._is_prefix = True
        return self._is_prefix

    def get_template_names(self):
        if self.is_prefix:
            # It is not a leaf, let's return the list view
            return super(PageElementEditableView, self).get_template_names()
        return ['pages/element.html']

    def get_context_data(self, **kwargs):
        context = super(
            PageElementEditableView, self).get_context_data(**kwargs)
        if self.is_prefix:
            url_kwargs = self.get_url_kwargs(**kwargs)
            path = url_kwargs.get('path')
            if isinstance(path, six.string_types):
                path = path.strip(self.URL_PATH_SEP)
            if path:
                url_kwargs.update({'path': path})
                if (self.account_url_kwarg and
                    self.account_url_kwarg not in url_kwargs):
                    url_kwargs.update({
                        self.account_url_kwarg: self.element.account})
                update_context_urls(context, {
                    'edit': {
                        # API end point to add content in the tree
                        'api_content': reverse(
                            'pages_api_edit_element', kwargs=url_kwargs),
                    },
                    'pages': {
                        'api_content': reverse(
                            'pages_api_edit_element', kwargs=url_kwargs),
                    }
                })
            else:
                if (self.account_url_kwarg and
                    self.account_url_kwarg in url_kwargs):
                    url_kwargs.pop('path', None)
                    update_context_urls(context, {
                        'edit': {
                            # API end point to add content in the tree
                            'api_content': reverse(
                                'pages_api_edit', kwargs=url_kwargs),
                        },
                        'pages': {
                            'api_content': reverse(
                                'pages_api_edit', kwargs=url_kwargs),
                        }
                    })
                else:
                    update_context_urls(context, {
                        'pages': {
                            'api_content': reverse('api_page_element_search',
                                kwargs=url_kwargs) + "?cut=pagebreak",
                        }
                    })
        else:
            context.update({'edit_perm': self.manages(self.element.account)})
            update_context_urls(context, {
                'api_page_element_base': reverse(
                    'pages_api_edit', args=(self.element.account,)),
                'edit': {
                    'api_content': reverse(
                        'pages_api_edit_element',
                        args=(self.element.account, self.element)),
                },
                'pages': {
                    'api_content': reverse(
                        'pages_api_edit_element',
                        args=(self.element.account, self.element)),
                    'api_follow': reverse('pages_api_follow',
                        args=(self.element,)),
                    'api_unfollow': reverse('pages_api_unfollow',
                        args=(self.element,)),
                    'api_downvote': reverse('pages_api_downvote',
                        args=(self.element,)),
                    'api_upvote': reverse('pages_api_upvote',
                        args=(self.element,)),
                    'api_comments': reverse('pages_api_comments',
                        args=(self.element,)),
                }
            })
            try:
                update_context_urls(context, {
                    'edit': {
                    'api_medias': reverse(
                        'uploaded_media_elements',
                        args=(self.element.account, self.element)),
                }})
            except NoReverseMatch:
                # There is no API end-point to upload POD assets (images, etc.)
                pass

        return context
