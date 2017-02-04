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

import logging, os, zipfile
from io import StringIO

from django.template.loader import get_template
from django.template.loader_tags import ExtendsNode
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from django.views.generic import DetailView, TemplateView, CreateView, View

from ..mixins import AccountMixin, ThemePackageMixin
from ..models import ThemePackage, get_active_theme
from ..compat import TemplateDoesNotExist, get_loaders
from ..utils import random_slug


LOGGER = logging.getLogger(__name__)


class ThemePackagesView(AccountMixin, TemplateView):

    template_name = "pages/theme.html"


class ThemePackagesCreateView(ThemePackageMixin, CreateView):

    model = ThemePackage
    template_name = "pages/create_package.html"
    fields = []

    def copy_default_template(self):
        if self.template_loaded:
            templates_dir = self.get_templates_dir(self.theme)
            to_path = os.path.join(templates_dir, self.template_loaded)

            loaders = get_loaders()
            template_source_loaders = tuple(loaders)
            for template_loader in template_source_loaders:
                try:
                    _, from_path = template_loader.load_template_source(
                        self.template_loaded, None)
                    self.copy_file(from_path, to_path)

                    # Check if template has ExtendsNodes
                    try:
                        #pylint:disable=no-member
                        template_nodelist = get_template(
                            self.template_loaded).template.nodelist
                    except AttributeError: # django < 1.8
                        template_nodelist = get_template(
                            self.template_loaded).nodelist
                    for node in template_nodelist:
                        if isinstance(node, ExtendsNode):
                            try:
                                extend_name = node.parent_name.resolve({})
                            except AttributeError: # django < 1.8
                                extend_name = node.get_parent({}).name
                            to_path = os.path.join(
                                templates_dir, extend_name)
                            _, from_path = template_loader.load_template_source(
                                extend_name, None)
                            self.copy_file(from_path, to_path)
                            break
                except TemplateDoesNotExist:
                    pass
                    #self.create_file(to_path)

    def create_package(self):
        from_static_dir = self.get_statics_dir(self.active_theme)
        from_templates_dir = self.get_templates_dir(self.active_theme)

        to_static_dir = self.get_statics_dir(self.theme)
        to_templates_dir = self.get_templates_dir(self.theme)

        if not os.path.exists(to_static_dir):
            os.makedirs(to_static_dir)
        if not os.path.exists(to_templates_dir):
            os.makedirs(to_templates_dir)

        # Copy files from active theme
        self.copy_files(from_static_dir, to_static_dir)
        self.copy_files(from_templates_dir, to_templates_dir)

        # Copy template user wants to edit
        # this template is not necessary in theme
        self.copy_default_template()

    def get_success_url(self):
        return "%s?redirect_url=%s&template_loaded=%s" % (
            reverse('uploaded_theme_edition', kwargs={'slug': self.theme.slug}),
            self.redirect_url,
            self.template_loaded)

    def get(self, request, *args, **kwargs):
        # Check active theme here
        # If active theme skip and redirect to file edition
        # with themepackage objects
        if self.active_theme.account == self.account:
            self.theme = self.active_theme
            self.copy_default_template()
            return HttpResponseRedirect(self.get_success_url())
        else:
            self.theme = None
            # otherwise create a new theme from active_theme
            return super(
                ThemePackagesCreateView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        slug = random_slug()
        while ThemePackage.objects.filter(slug=slug).count() > 0:
            slug = random_slug()
        name = self.active_theme.name
        slug = "%s-%s" % (name, slug)
        self.theme = ThemePackage.objects.create(
            slug=slug,
            account=self.account,
            name=name)
        self.create_package()
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super(ThemePackagesCreateView,
            self).get_context_data(**kwargs)
        context.update({
            'template_loaded': self.template_loaded,
            'redirect_url': self.redirect_url})
        return context

    def dispatch(self, request, *args, **kwargs):
        self.template_loaded = request.GET.get('template_loaded', None)
        self.redirect_url = request.GET.get('redirect_url', None)
        self.active_theme = get_active_theme()
        return super(ThemePackagesCreateView, self).dispatch(
            request, *args, **kwargs)

class ThemePackagesEditView(ThemePackageMixin, DetailView):

    model = ThemePackage
    template_name = "pages/file_edition.html"

    def get_context_data(self, **kwargs):
        context = super(ThemePackagesEditView, self).get_context_data(**kwargs)
        themepackage = context['themepackage']
        static_dir = self.get_statics_dir(themepackage)
        templates_dir = self.get_templates_dir(themepackage)
        templates = self.get_file_tree(templates_dir)
        statics = self.get_file_tree(static_dir)
        context.update({
            'templates': templates['templates'],
            'statics': statics['static'],
            'template_loaded': self.template_loaded,
            'redirect_url': self.redirect_url})
        return context

    def dispatch(self, request, *args, **kwargs):
        self.template_loaded = request.GET.get('template_loaded', None)
        self.redirect_url = request.GET.get('redirect_url', None)
        return super(ThemePackagesEditView, self).dispatch(
            request, *args, **kwargs)


class ThemePackageDownloadView(ThemePackageMixin, View):

    def get(self, *args, **kwargs): #pylint:disable=unused-argument
        theme = ThemePackage.objects.get(slug=self.kwargs.get('slug'))
        from_static_dir = self.get_statics_dir(theme)
        from_templates_dir = self.get_templates_dir(theme)

        content = StringIO()
        zipf = zipfile.ZipFile(content, mode="w")

        zipf = self.write_zipfile(zipf, from_static_dir, 'public')
        zipf = self.write_zipfile(zipf, from_templates_dir, 'templates')

        zipf.close()
        content.seek(0)

        resp = HttpResponse(content.read(), content_type='application/x-zip')
        resp['Content-Disposition'] = 'attachment; filename="{}"'.format(
                "%s.zip" % theme.slug)
        return resp
