# Copyright (c) 2015, Djaodjin Inc.
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

#pylint: disable=no-init,no-member
#pylint: disable=old-style-class,maybe-no-member

import re

from bs4 import BeautifulSoup
from django.conf import settings
from rest_framework import status
from rest_framework.mixins import CreateModelMixin
from rest_framework import generics
from rest_framework.response import Response

from pages.models import PageElement, UploadedImage
from pages.serializers import PageElementSerializer
from pages.mixins import AccountMixin


class PagesElementListAPIView(AccountMixin, generics.ListCreateAPIView):
    pass

class PageElementDetail(AccountMixin, CreateModelMixin,
                        generics.RetrieveUpdateDestroyAPIView):
    """
    Create or Update an editable element on a ``PageElement``.
    """
    serializer_class = PageElementSerializer
    lookup_field = 'slug'
    lookup_url_kwarg = 'slug'

    def get_queryset(self):
        kwargs = {self.lookup_field: self.kwargs.get(self.lookup_url_kwarg)}
        account_slug = self.kwargs.get(self.account_url_kwarg, None)
        if account_slug:
            kwargs.update({'account__slug': account_slug})
        return PageElement.objects.filter(**kwargs) #pylint:disable=star-args

    @staticmethod
    def clean_text(text):
        formatted_text = re.sub(r'[\ ]{2,}', '', text)
        if formatted_text.startswith('\n'):
            formatted_text = formatted_text[1:]
        if formatted_text.endswith('\n'):
            formatted_text = formatted_text[:len(formatted_text)-1]
        return formatted_text

    def write_html(self, path, new_id):
        with open(path, "r") as myfile:
            soup = BeautifulSoup(myfile, "html.parser")
            soup_elements = soup.find_all(self.request.DATA['tag'].lower())
            if len(soup_elements) > 1:
                for element in soup_elements:
                    if element.string:
                        formatted_text = self.clean_text(element.string)
                        if formatted_text == self.request.DATA['old_text']:
                            soup_element = element
                            break
                if not soup_element:
                    # XXX - raise an exception
                    pass
            else:
                soup_element = soup_elements[0]

            soup_element['id'] = new_id
            html = soup.prettify("utf-8")
            changed = True
        if changed:
            # write html to save new id
            with open(path, "w") as myfile:
                myfile.write(html)

    def perform_create(self, serializer):
        return serializer.save(account=self.get_account())

    def update_or_create_pagelement(self, request, *args, **kwargs):
        #pylint: disable=unused-argument
        """
        Update or create a ``PageElement`` with a text overlay
        of the default text present in the HTML template.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        queryset = self.get_queryset()
        if queryset.exists():
            self.object = queryset.get()
            response_status = status.HTTP_200_OK
            self.perform_update(serializer)
        else:
            self.object = self.perform_create(serializer)
            response_status = status.HTTP_201_CREATED

        if self.object.slug.startswith('djmedia-'):
            text = request.DATA['text']
            #check S3 version exists
            if not 's3.amazon' in text:
                try:
                    upload_image = UploadedImage.objects.get(
                        uploaded_file_temp=text.replace('/media/', ''))
                    if upload_image.uploaded_file:
                        text = \
                            settings.S3_URL + '/' + text.replace('/media/', '')
                except: #pylint: disable=bare-except
                    pass

        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=response_status, headers=headers)

    def put(self, request, *args, **kwargs):
        return self.update_or_create_pagelement(request, *args, **kwargs)
