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
import markdown

from bs4 import BeautifulSoup
from django.core.context_processors import csrf
from django.views.generic import ListView, DetailView
from django.template import loader, Context
from django.template.response import TemplateResponse
from django.views.generic import TemplateView

from .mixins import AccountMixin
from .models import PageElement


class PageMixin(AccountMixin):
    """
    Display or Edit a ``Page`` of a ``Project``.

    """
    edition_tools_template_name = 'pages/edition_tools.html'

    def add_edition_tools(self, content, context=None):
        """
        Inject the edition tools into the html *content* and return
        a BeautifulSoup object of the resulting content + tools.
        """
        if context is None:
            context = {}
        context.update(csrf(self.request))
        template = loader.get_template(self.edition_tools_template_name)
        soup = BeautifulSoup(content, 'html5lib')
        if soup and soup.body:
            soup.body.append(
                BeautifulSoup(template.render(Context(context)), 'html.parser'))
            return soup
        return None

    @staticmethod
    def insert_formatted(editable, new_text):
        new_text = BeautifulSoup(new_text, 'html5lib')
        for image in new_text.find_all('img'):
            image['style'] = "max-width:100%"
        editable.name = 'div'
        editable.clear()
        editable.append(new_text)

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
        content_type = response.get('content-type', '')
        if content_type.startswith('text/html'):
            soup = self.add_edition_tools(response.content)
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


class UploadedTemplatesView(TemplateView):

    template_name = "pages/uploaded_template_list.html"
