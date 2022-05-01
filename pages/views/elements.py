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
from ..helpers import get_extra, update_context_urls
from ..models import RelationShip
from ..mixins import AccountMixin, TrailMixin


LOGGER = logging.getLogger(__name__)


class PageElementView(TrailMixin, AccessiblesMixin, TemplateView):
    """
    When {path} points to an internal node in the content DAG, an index
    page is created that contains the children (up to `pagebreak`)
    of that node that are both visible and searchable.
    """
    template_name = 'pages/index.html'

    def get_reverse_kwargs(self):
        """
        List of kwargs taken from the url that needs to be passed through
        to ``reverse``.
        """
        return [self.path_url_kwarg]

    def get_url_kwargs(self, **kwargs):
        url_kwargs = {}
        if not kwargs:
            kwargs = self.kwargs
        for url_kwarg in self.get_reverse_kwargs():
            url_kwarg_val = kwargs.get(url_kwarg, None)
            if url_kwarg_val:
                url_kwargs.update({url_kwarg: url_kwarg_val})
        return url_kwargs

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
        candidates = []
        if self.element:
            candidates += ["pages/%s.html" % layout
                for layout in get_extra(self.element, 'layouts', [])]
        if self.is_prefix:
            # It is not a leaf, let's return the list view
            candidates += super(PageElementView, self).get_template_names()
        else:
            candidates += ['pages/element.html']
        return candidates

    def get_context_data(self, **kwargs):
        context = super(PageElementView, self).get_context_data(**kwargs)
        url_kwargs = self.get_url_kwargs(**kwargs)
        path = url_kwargs.pop('path', None)
        update_context_urls(context, {
            # We cannot use `kwargs=url_kwargs` here otherwise
            # it will pick up the overriden definition of
            # `get_reverse_kwargs`  in PageElementEditableView.
            'pages_index': reverse('pages_index')
        })
        if self.is_prefix:
            if isinstance(path, six.string_types):
                path = path.strip(self.URL_PATH_SEP)
            if path:
                url_kwargs = {'path': path}
                if self.manages(self.element.account):
                    context.update({
                        'edit_perm': self.manages(self.element.account)
                    })
                    url_kwargs.update({
                        self.account_url_kwarg: self.element.account})
                    update_context_urls(context, {
                        'api_content': reverse('pages_api_edit_element',
                            kwargs=url_kwargs),
                    })
                else:
                    update_context_urls(context, {
                      'api_content': reverse('api_content', kwargs=url_kwargs),
                    })
            else:
                update_context_urls(context, {
                    # We cannot use `kwargs=url_kwargs` here otherwise
                    # it will pick up the overriden definition of
                    # `get_reverse_kwargs`  in PageElementEditableView.
                    'api_content': reverse('api_content_index'),
                })
        else:
            url_kwargs = {'path': self.element.slug}
            if self.manages(self.element.account):
                context.update({
                    'edit_perm': self.manages(self.element.account)
                })
                url_kwargs.update({
                    self.account_url_kwarg: self.element.account})
                update_context_urls(context, {
                    'api_content': reverse('pages_api_edit_element',
                        kwargs=url_kwargs),
                })
                try:
                    update_context_urls(context, {
                        'edit': {
                        'api_medias': reverse(
                            'uploaded_media_elements',
                            args=(self.element.account, self.element)),
                    }})
                except NoReverseMatch:
                    # There is no API end-point to upload POD assets (images,
                    # etc.)
                    pass

            else:
                update_context_urls(context, {
                    'api_content': reverse('api_content',
                        kwargs=url_kwargs),
                })
            update_context_urls(context, {
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
            })
        return context


class PageElementEditableView(AccountMixin, PageElementView):
    """
    When {path} points to an internal node in the content DAG, an index
    page is created that contains the direct children of that belongs
    to the `account`.
    """
    template_name = 'pages/editables.html'
    breadcrumb_url = 'pages_editables_element'

    def get_reverse_kwargs(self):
        """
        List of kwargs taken from the url that needs to be passed through
        to ``reverse``.
        """
        kwargs_keys = super(PageElementEditableView, self).get_reverse_kwargs()
        if self.account_url_kwarg:
            kwargs_keys += [self.account_url_kwarg]
        return kwargs_keys

    def get_context_data(self, **kwargs):
        context = super(
            PageElementEditableView, self).get_context_data(**kwargs)
        url_kwargs = self.get_url_kwargs(**kwargs)
        path = url_kwargs.pop('path', None)
        update_context_urls(context, {
            'pages_index': reverse('pages_editables_index', kwargs=url_kwargs)
        })
        if self.is_prefix:
            if isinstance(path, six.string_types):
                path = path.strip(self.URL_PATH_SEP)
            if not path:
                update_context_urls(context, {
                    'api_content': reverse('pages_api_editables_index',
                        kwargs=url_kwargs),
                })
        return context
