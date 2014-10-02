# Copyright (c) 2014, DjaoDjin inc.
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

from bs4 import BeautifulSoup
from django.views.generic import TemplateView
from pages.models import PageElement
from django.template.response import TemplateResponse
import markdown, re

from .mixins import AccountMixin

class PageView(AccountMixin, TemplateView):
    """
    Display or Edit a ``Page`` of a ``Project``.

    """

    http_method_names = ['get']


    def get_context_data(self, **kwargs):
        context = super(PageView, self).get_context_data(**kwargs)
        context.update({'template_name': self.template_name})
        return context

    def get(self, request, *args, **kwargs):
        response = super(PageView, self).get(request, *args, **kwargs)
        if self.template_name and isinstance(response, TemplateResponse):
            response.render()
            soup = BeautifulSoup(response.content)
            for editable in soup.find_all(class_="editable"):
                try:
                    id_element = editable['id']
                except KeyError:
                    continue
                try:
                    edit = PageElement.objects.filter(slug=id_element)
                    account = self.get_account()
                    if account:
                        edit = edit.get(account=account)
                    else:
                        edit = edit[0]
                    new_text = re.sub(r'[\ ]{2,}', '', edit.text)
                    if 'edit-markdown' in editable['class']:
                        new_text = markdown.markdown(new_text)
                        new_text = BeautifulSoup(new_text)
                        editable.name = 'div'
                        editable.string = ''
                        children_done = []
                        for element in new_text.find_all():
                            if element.name != 'html' and\
                                element.name != 'body':
                                if len(element.findChildren()) > 0:
                                    element.append(element.findChildren()[0])
                                    children_done += [element.findChildren()[0]]
                                if not element in children_done:
                                    editable.append(element)
                    else:
                        editable.string = new_text
                except PageElement.DoesNotExist:
                    pass
            response.content = soup.prettify()
        return response
