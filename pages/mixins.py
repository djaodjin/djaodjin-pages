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

import logging

import markdown
from bs4 import BeautifulSoup
from django.http import Http404
from django.utils._os import safe_join
from rest_framework.generics import get_object_or_404

from . import settings
from .compat import import_string, reverse, six, urlsplit
from .models import MediaTag, PageElement, get_active_theme
from .extras import AccountMixinBase


LOGGER = logging.getLogger(__name__)


class AccountMixin(AccountMixinBase, settings.EXTRA_MIXIN):
    pass


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


class UploadedImageMixin(object):

    def build_filter_list(self, validated_data):
        items = validated_data.get('items')
        filter_list = []
        if items:
            for item in items:
                location = item['location']
                parts = urlsplit(location)
                if parts.netloc == self.request.get_host():
                    location = parts.path
                filter_list += [location]
        return filter_list

    def list_media(self, storage, filter_list, prefix='.'):
        """
        Return a list of media from default storage
        """
        #pylint:disable=too-many-locals
        results = []
        total_count = 0
        if prefix.startswith('/'):
            prefix = prefix[1:]
        try:
            dirs, files = storage.listdir(prefix)
            for media in files:
                if prefix and prefix != '.':
                    media = prefix + '/' + media
                if not media.endswith('/') and media != "":
                    total_count += 1
                    location = storage.url(media)
                    try:
                        updated_at = storage.get_modified_time(media)
                    except AttributeError: # Django<2.0
                        updated_at = storage.modified_time(media)
                    normalized_location = location.split('?')[0]
                    if (filter_list is None
                        or normalized_location in filter_list):
                        tags = ",".join(list(MediaTag.objects.filter(
                            location=normalized_location).values_list(
                            'tag', flat=True)))
                        results += [
                            {'location': location,
                            'tags': tags,
                            'updated_at': updated_at
                            }]
            for asset_dir in dirs:
                dir_results, dir_total_count = self.list_media(
                    storage, filter_list, prefix=prefix + '/' + asset_dir)
                results += dir_results
                total_count += dir_total_count
        except OSError:
            if storage.exists('.'):
                LOGGER.exception(
                    "Unable to list objects in %s.", storage.__class__.__name__)
        except storage.connection_response_error:
            LOGGER.exception(
                "Unable to list objects in 's3://%s/%s/%s'.",
                storage.bucket_name, storage.location, prefix)

        # sort results by updated_at to sort by created_at.
        # Media are not updated, so updated_at = created_at
        return results, total_count


class ThemePackageMixin(AccountMixin):

    theme_url_kwarg = 'theme'

    @property
    def theme(self):
        if not hasattr(self, '_theme'):
            self._theme = self.kwargs.get(self.theme_url_kwarg)
            if not self._theme:
                self._theme = get_active_theme()
        return self._theme

    @staticmethod
    def get_templates_dir(theme):
        if isinstance(settings.THEME_DIR_CALLABLE, six.string_types):
            settings.THEME_DIR_CALLABLE = import_string(
                settings.THEME_DIR_CALLABLE)
        theme_dir = settings.THEME_DIR_CALLABLE(theme)
        return safe_join(theme_dir, 'templates')

    @staticmethod
    def get_statics_dir(theme):
        return safe_join(settings.PUBLIC_ROOT, theme, 'static')


class UpdateEditableMixin(object):
    """
    Edit an element in a page.
    """
    @staticmethod
    def insert_formatted(editable, new_text):
        new_text = BeautifulSoup(new_text, 'html5lib')
        for image in new_text.find_all('img'):
            image['style'] = "max-width:100%"
        if editable.name == 'div':
            editable.clear()
            editable.append(new_text)
        else:
            editable.string = "ERROR : Impossible to insert HTML into \
                \"<%s></%s>\" element. It should be \"<div></div>\"." %\
                (editable.name, editable.name)
            editable['style'] = "color:red;"
            # Prevent edition of error notification
            editable['class'] = editable['class'].remove("editable")

    @staticmethod
    def insert_currency(editable, new_text):
        amount = float(new_text)
        editable.string = "$%.2f" % (amount/100)

    @staticmethod
    def insert_markdown(editable, new_text):
        new_text = markdown.markdown(new_text,)
        new_text = BeautifulSoup(new_text, 'html.parser')
        for image in new_text.find_all('img'):
            image['style'] = "max-width:100%"
        editable.name = 'div'
        editable.string = ''
        children_done = []
        for element in new_text.find_all():
            if element.name not in ('html', 'body'):
                if element.findChildren():
                    for sub_el in element.findChildren():
                        element.append(sub_el)
                        children_done += [sub_el]
                if not element in children_done:
                    editable.append(element)
