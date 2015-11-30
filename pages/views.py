# Copyright (c) 2015, DjaoDjin inc.
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
import markdown, os, random, string, shutil

from bs4 import BeautifulSoup
from django.conf import settings as django_settings
from django.template.loader import find_template_loader
from django.template.base import TemplateDoesNotExist
from django.core.context_processors import csrf
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.views.generic import ListView, DetailView, TemplateView, CreateView
from django.template import loader, Context, RequestContext
from django.template.response import TemplateResponse

from .mixins import AccountMixin, ThemePackageMixin
from .models import PageElement, ThemePackage, get_active_theme
from . import settings


def inject_edition_tools(response, request=None, context=None,
                    body_top_template_name="pages/_body_top.html",
                    body_bottom_template_name="pages/_body_bottom.html"):
    """
    Inject the edition tools into the html *content* and return
    a BeautifulSoup object of the resulting content + tools.
    """
    soup = None
    content_type = response.get('content-type', '')
    if content_type.startswith('text/html'):
        if context is None:
            context = {}
        context.update(csrf(request))
        if not isinstance(context, Context):
            context = RequestContext(request, context)
        template = loader.get_template(body_top_template_name)
        body_top = template.render(context).strip()
        if body_top:
            if not soup:
                soup = BeautifulSoup(response.content, 'html5lib')
            if soup and soup.body:
                # Implementation Note: we have to use ``.body.next`` here
                # because html5lib "fixes" our HTML by adding missing
                # html/body tags. Furthermore if we use
                #``soup.body.insert(1, BeautifulSoup(body_top, 'html.parser'))``
                # instead, later on ``soup.find_all(class_=...)`` returns
                # an empty set though ``soup.prettify()`` outputs the full
                # expected HTML text.
                soup.body.insert(1, BeautifulSoup(body_top).body.next)
        template = loader.get_template(body_bottom_template_name)
        body_bottom = template.render(context).strip()
        if body_bottom:
            if not soup:
                soup = BeautifulSoup(response.content, 'html5lib')
            if soup and soup.body:
                soup.body.append(BeautifulSoup(body_bottom, 'html.parser'))
    return soup


class PageMixin(AccountMixin):
    """
    Display or Edit a ``Page`` of a ``Project``.

    """
    body_top_template_name = "pages/_body_top.html"
    body_bottom_template_name = "pages/_body_bottom.html"

    def add_edition_tools(self, response, context=None):
        return inject_edition_tools(
            response, request=self.request, context=context,
            body_top_template_name=self.body_top_template_name,
            body_bottom_template_name=self.body_bottom_template_name)

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
            if element.name != 'html' and\
                element.name != 'body':
                if len(element.findChildren()) > 0:
                    for sub_el in element.findChildren():
                        element.append(sub_el)
                        children_done += [sub_el]
                if not element in children_done:
                    editable.append(element)

    def get(self, request, *args, **kwargs):
        #pylint: disable=too-many-statements, too-many-locals
        response = super(PageMixin, self).get(request, *args, **kwargs)
        if self.template_name and isinstance(response, TemplateResponse):
            response.render()
        soup = self.add_edition_tools(response,
            {'redirect_url': request.path,
            'template_loaded': self.template_name})
        if not soup:
            content_type = response.get('content-type', '')
            if content_type.startswith('text/html'):
                soup = BeautifulSoup(response.content, 'html5lib')
        if soup:
            editable_ids = set([])
            for editable in soup.find_all(class_="editable"):
                try:
                    editable_ids |= set([editable['id']])
                except KeyError:
                    continue

            kwargs = {'slug__in': editable_ids}
            if self.account:
                kwargs.update({'account': self.account})
            for edit in PageElement.objects.filter(**kwargs):
                editable = soup.find(id=edit.slug)
                new_text = edit.text
                if editable:
                    if 'edit-formatted' in editable['class']:
                        self.insert_formatted(
                            editable, new_text)
                    elif 'edit-markdown' in editable['class']:
                        self.insert_markdown(editable, new_text)
                    elif 'edit-currency' in editable['class']:
                        self.insert_currency(editable, new_text)
                    elif 'droppable-image' in editable['class']:
                        editable['src'] = edit.text
                    else:
                        editable.string = new_text
            response.content = soup.prettify()
        return response


class PageView(PageMixin, TemplateView):

    http_method_names = ['get']


class PageElementListView(ListView):
    model = PageElement
    tag = None

    def get_queryset(self):
        queryset = self.model.objects.all()
        if self.tag:
            queryset = queryset.filter(tag=self.tag)
        return queryset


class PageElementDetailView(DetailView):
    model = PageElement


class ThemePackagesView(TemplateView):

    template_name = "pages/package_list.html"


class ThemePackagesCreateView(ThemePackageMixin, CreateView):

    model = ThemePackage
    template_name = "pages/create_package.html"

    def copy_default_template(self):
        if self.template_loaded:
            templates_dir = os.path.join(
                settings.TEMPLATES_ROOT, self.theme.slug)
            loaders = []
            for loader_name in django_settings.TEMPLATE_LOADERS:
                loader = find_template_loader(loader_name)
                if loader is not None:
                    loaders.append(loader)
            template_source_loaders = tuple(loaders)
            for loader in template_source_loaders:
                try:
                    _, template_path = loader.load_template_source(self.template_loaded, None)
                    if not os.path.exists(
                        os.path.dirname(os.path.join(
                            templates_dir, self.template_loaded))):
                        os.makedirs(os.path.dirname(
                            os.path.join(templates_dir, self.template_loaded)))
                    if not os.path.exists(
                        os.path.join(templates_dir, self.template_loaded)):
                        shutil.copyfile(
                            template_path,
                            os.path.join(templates_dir, self.template_loaded))
                    return
                except TemplateDoesNotExist:
                    pass

    def create_package(self):
        static_dir = os.path.join(settings.PUBLIC_ROOT, self.theme.slug)
        templates_dir = os.path.join(settings.TEMPLATES_ROOT, self.theme.slug)
        if not os.path.exists(static_dir):
            os.mkdir(static_dir)
        if not os.path.exists(templates_dir):
            os.mkdir(templates_dir)
        self.copy_default_template()

    @staticmethod
    def random_slug():
        return ''.join(
            random.choice(string.ascii_lowercase + string.digits)\
                for count in range(20))

    def get_success_url(self):
        return "%s?redirect_url=%s&template_loaded=%s" % (
            reverse('uploaded_theme_edition', kwargs={'slug': self.theme.slug}),
            self.redirect_url,
            self.template_loaded)


    def get(self, request, *args, **kwargs):
        self.theme = get_active_theme()
        # Check active theme here
        # If active theme skip and redirect to file edition
        # with themepackage objects
        if self.theme:
            self.copy_default_template()
            return HttpResponseRedirect(self.get_success_url())
        else:
            self.theme = None
            # otherwise create one with selected templates
            return super(
                ThemePackagesCreateView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        account = self.account
        slug = self.random_slug()
        while ThemePackage.objects.filter(slug=slug).count() > 0:
            slug = self.random_slug()
        name = ""
        if account:
            name += account.slug
        name += "-%s" % slug
        self.theme = ThemePackage.objects.create(
            slug=slug,
            account=account,
            name=name)
        self.create_package()
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super(ThemePackagesCreateView, self).get_context_data(**kwargs)
        context.update({
            'template_loaded': self.template_loaded,
            'redirect_url': self.redirect_url})
        return context

    def dispatch(self, request, *args, **kwargs):
        self.template_loaded = request.GET.get('template_loaded', None)
        self.redirect_url = request.GET.get('redirect_url', None)
        return super(ThemePackagesCreateView, self).dispatch(
            request, *args, **kwargs)

class ThemePackagesEditView(ThemePackageMixin, DetailView):

    model = ThemePackage
    template_name = "pages/file_edition.html"

    def get_context_data(self, **kwargs):
        context = super(ThemePackagesEditView, self).get_context_data(**kwargs)
        themepackage = context['themepackage']
        static_dir = os.path.join(settings.PUBLIC_ROOT, themepackage.slug)
        templates_dir = os.path.join(settings.TEMPLATES_ROOT, themepackage.slug)
        templates = self.get_file_tree(templates_dir)
        statics = self.get_file_tree(static_dir)
        context.update({
            'templates': templates[themepackage.slug],
            'statics': statics[themepackage.slug],
            'template_loaded': self.template_loaded,
            'redirect_url': self.redirect_url})
        return context

    def dispatch(self, request, *args, **kwargs):
        self.template_loaded = request.GET.get('template_loaded', None)
        self.redirect_url = request.GET.get('redirect_url', None)
        return super(ThemePackagesEditView, self).dispatch(
            request, *args, **kwargs)
