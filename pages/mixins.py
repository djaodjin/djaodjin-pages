# Copyright (c) 2022 DjaoDjin inc.
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

from __future__ import unicode_literals

import logging

from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.http import Http404
from django.utils.translation import ugettext as _
from rest_framework.generics import get_object_or_404

from . import settings
from .compat import reverse, is_authenticated
from .models import PageElement
from .utils import get_account_model

LOGGER = logging.getLogger(__name__)


class AccountMixin(object):
    """
    Mixin to use in views that will retrieve an account object (out of
    ``account_queryset``) associated to a slug parameter (``account_url_kwarg``)
    in the URL.
    If either ``account_url_kwarg`` is ``None`` or absent from the URL pattern,
    ``account`` will default to the ``request.user`` when the account model is
    compatible with the `User` model, else ``account`` will be ``None``.
    """
    account_queryset = get_account_model().objects.all()
    account_lookup_field = settings.ACCOUNT_LOOKUP_FIELD
    account_url_kwarg = settings.ACCOUNT_URL_KWARG

    @property
    def account(self):
        if not hasattr(self, '_account'):
            if (self.account_url_kwarg is not None
                and self.account_url_kwarg in self.kwargs):
                if self.account_queryset is None:
                    raise ImproperlyConfigured(
                        "%(cls)s.account_queryset is None. Define "
                        "%(cls)s.account_queryset." % {
                            'cls': self.__class__.__name__
                        }
                    )
                if self.account_lookup_field is None:
                    raise ImproperlyConfigured(
                        "%(cls)s.account_lookup_field is None. Define "
                        "%(cls)s.account_lookup_field as the field used "
                        "to retrieve accounts in the database." % {
                            'cls': self.__class__.__name__
                        }
                    )
                kwargs = {'%s__exact' % self.account_lookup_field:
                    self.kwargs.get(self.account_url_kwarg)}
                try:
                    self._account = self.account_queryset.filter(**kwargs).get()
                except self.account_queryset.model.DoesNotExist:
                    #pylint: disable=protected-access
                    raise Http404(_("No %(verbose_name)s found matching"\
                        "the query") % {'verbose_name':
                        self.account_queryset.model._meta.verbose_name})
            else:
                if (isinstance(get_account_model(), get_user_model()) and
                    is_authenticated(self.request)):
                    self._account = self.request.user
                self._account = None
        return self._account

    def get_context_data(self, **kwargs):
        context = super(AccountMixin, self).get_context_data(**kwargs)
        context.update({'account': self.account})
        return context

    def get_reverse_kwargs(self):
        """
        List of kwargs taken from the url that needs to be passed through
        to ``get_success_url``.
        """
        if self.account_url_kwarg:
            return [self.account_url_kwarg]
        return []

    def get_url_kwargs(self, **kwargs):
        url_kwargs = {}
        if not kwargs:
            kwargs = self.kwargs
        for url_kwarg in self.get_reverse_kwargs():
            url_kwarg_val = kwargs.get(url_kwarg, None)
            if url_kwarg_val:
                url_kwargs.update({url_kwarg: url_kwarg_val})
        return url_kwargs


class TrailMixin(object):
    """
    Generate a trail of PageElement based on a path.
    """
    URL_PATH_SEP = '/'
    path_url_kwarg = 'path'
    breadcrumb_url = 'pages_element'

    @property
    def breadcrumbs(self):
        if not hasattr(self, '_breadcrumbs'):
            self._breadcrumbs = []
            parts = self.path.strip(self.URL_PATH_SEP).split(self.URL_PATH_SEP)
            title_by_slug = dict(PageElement.objects.filter(
                slug__in=parts).values_list('slug', 'title'))
            for idx, part in enumerate(parts):
                title = title_by_slug.get(part)
                if title:
                    url_kwargs = self.get_url_kwargs()
                    url_kwargs.update({
                        self.path_url_kwarg: self.URL_PATH_SEP.join(
                            parts[:idx + 1])})
                    self._breadcrumbs += [(part, title,
                        reverse(self.breadcrumb_url, kwargs=url_kwargs))]
        return self._breadcrumbs

    @property
    def element(self):
        if not hasattr(self, '_element'):
            path = self.path.strip(self.URL_PATH_SEP)
            if not path:
                self._element = None
            else:
                parts = path.split(self.URL_PATH_SEP)
                self._element = get_object_or_404(
                    PageElement.objects.all(), slug=parts[-1])
        return self._element

    @property
    def path(self):
        if not hasattr(self, '_path'):
            self._path = self.kwargs.get(self.path_url_kwarg, '')
            if self._path and not self._path.startswith(self.URL_PATH_SEP):
                self._path = self.URL_PATH_SEP + self._path
        return self._path

    @property
    def full_path(self):
        if not hasattr(self, '_full_path'):
            self._full_path = self.URL_PATH_SEP.join(
                [str(elem) for elem in self.get_full_element_path(self.path)])
            if (self._full_path and
                not self._full_path.startswith(self.URL_PATH_SEP)):
                self._full_path = self.URL_PATH_SEP + self._full_path
        return self._full_path

    def get_full_element_path(self, path):
        if not path:
            return []
        results = []
        parts = path.strip(self.URL_PATH_SEP).split(self.URL_PATH_SEP)
        if parts:
            element = get_object_or_404(
                PageElement.objects.all(), slug=parts[-1])
            candidates = element.get_parent_paths(hints=parts[:-1])
            if not candidates:
                raise Http404("%s could not be found." % path)
            # XXX Implementation Note: if we have multiple candidates,
            # it means the hints were not enough to select a single path.
            # This is still OK to pick the first candidate as the breadcrumbs
            # should take a user back to the top-level page.
            if len(candidates) > 1:
                LOGGER.debug("get_full_element_path has multiple candidates"\
                    " for '%s': %s", path, candidates)
            results = candidates[0]
        return results

    def get_reverse_kwargs(self):
        """
        List of kwargs taken from the url that needs to be passed through
        to ``reverse``.
        """
        reverse_url_kwargs = super(TrailMixin, self).get_reverse_kwargs()
        reverse_url_kwargs += [self.path_url_kwarg]
        return reverse_url_kwargs

    def get_context_data(self, **kwargs):
        context = super(TrailMixin, self).get_context_data(**kwargs)
        context.update({'breadcrumbs': self.breadcrumbs})
        return context


class PageElementMixin(object):

    URL_PATH_SEP = '/'
    path_url_kwarg = 'path'
    element_field = 'slug'
    element_url_kwarg = 'slug'

    @property
    def element(self):
        if not hasattr(self, '_element'):
            element_value = None
            element_url_kwarg = self.element_url_kwarg or self.element_field
            if element_url_kwarg in self.kwargs:
                element_value = self.kwargs[element_url_kwarg]
            else:
                path = self.kwargs.get(self.path_url_kwarg, '').strip(
                    self.URL_PATH_SEP)
                if not path:
                    raise Http404()
                parts = path.split(self.URL_PATH_SEP)
                element_value = parts[-1]
            filter_kwargs = {self.element_field: element_value}
            self._element = get_object_or_404(
                PageElement.objects.all(), **filter_kwargs)
        return self._element
