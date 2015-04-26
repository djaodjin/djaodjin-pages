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

import re
import markdown

from bs4 import BeautifulSoup
from django.template.response import TemplateResponse
from django.views.generic import TemplateView

from .mixins import AccountMixin
from .models import PageElement


class PageView(AccountMixin, TemplateView):
    """
    Display or Edit a ``Page`` of a ``Project``.

    """
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):#pylint: disable=too-many-statements, too-many-locals
        response = super(PageView, self).get(request, *args, **kwargs)
        if self.template_name and isinstance(response, TemplateResponse):
            response.render()
            soup = BeautifulSoup(response.content)
            account = self.get_account()
            if account:
                page_elements = PageElement.objects.filter(account=account)
            else:
                page_elements = PageElement.objects.all()
            for editable in soup.find_all(class_="editable"):
                try:
                    id_element = editable['id']
                except KeyError:
                    continue
                try:
                    edit = page_elements.get(slug=id_element)
                    new_text = re.sub(r'[\ ]{2,}', '', edit.text)
                    if 'edit-markdown' in editable['class']:
                        new_text = markdown.markdown(new_text)
                        new_text = BeautifulSoup(new_text)
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
                    else:
                        editable.string = new_text
                except PageElement.DoesNotExist:
                    pass

            #load all media pageelemeny
            db_medias = page_elements.filter(slug__startswith='djmedia-')
            for media in soup.find_all(class_="droppable-image"):
                try:
                    id_element = media['id']
                except KeyError:
                    continue
                try:
                    db_media = db_medias.get(slug=id_element)
                    if db_media.image:
                        if db_media.image.uploaded_file:
                            media['src'] = db_media.image.uploaded_file
                        else:
                            media['src'] = db_media.image.uploaded_file_cache
                except PageElement.DoesNotExist:
                    continue
            response.content = soup.prettify()
        return response


class UploadedTemplatesView(TemplateView):

    template_name = "pages/uploaded_template_list.html"
