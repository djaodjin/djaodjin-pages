# Copyright (c) 2014, Djaodjin Inc.
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

#pylint: disable=no-init,no-member,unused-variable
#pylint: disable=old-style-class,line-too-long,maybe-no-member

import os, random, string, re

from rest_framework.response import Response
from rest_framework import generics
from rest_framework import status
from rest_framework.parsers import FileUploadParser
from pages.models import PageElement, UploadedImage
from pages.serializers import PageElementSerializer, UploadedImageSerializer
from bs4 import BeautifulSoup
from django.conf import settings

from rest_framework.serializers import ValidationError
from rest_framework.views import APIView

from .mixins import AccountMixin

class PageElementDetail(AccountMixin, generics.RetrieveUpdateDestroyAPIView):
    """
    Create or Update an editable element on a ``Page``.
    """
    model = PageElement
    serializer_class = PageElementSerializer

    @staticmethod
    def clean_text(text):
        formatted_text = re.sub(r'[\ ]{2,}', '', text)
        if formatted_text.startswith('\n'):
            formatted_text = formatted_text[1:]
        if formatted_text.endswith('\n'):
            formatted_text = formatted_text[:len(formatted_text)-1]
        return formatted_text

    def update_or_create_pagelement(self, request, *args, **kwargs):#pylint: disable=too-many-locals,unused-argument
        """
        Update an existing PageElement if id provided
        If no id provided create a pagelement with new id,
        write new html and return id to live template
        """
        partial = kwargs.pop('partial', False)
        self.object = self.get_object_or_none()
        serializer = self.get_serializer(self.object, data=request.DATA,
                                         files=request.FILES, partial=partial)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            self.pre_save(serializer.object)
        except ValidationError as err:
            # full_clean on model instance may be called in pre_save,
            # so we have to handle eventual errors.
            return Response(err.message_dict, status=status.HTTP_400_BAD_REQUEST)

        if self.object is None:
            if kwargs.get('slug') != 'undefined':
                new_id = kwargs.get('slug')
            else:
            # Create a new id
                new_id = ''.join(random.choice(string.lowercase) for i in range(10))
                while PageElement.objects.filter(slug__exact=new_id).count() > 0:
                    new_id = ''.join(random.choice(string.lowercase) for i in range(10))

            # Create a pageelement
            pagelement = PageElement(slug=new_id, text=request.DATA['text'])
            account = self.get_account()
            if account:
                pagelement.account = account
            serializer = self.get_serializer(pagelement, data=request.DATA,
                files=request.FILES, partial=partial)
            self.object = serializer.save(force_insert=True)

            changed = False

            for directory in settings.TEMPLATE_DIRS:
                for (dirpath, dirnames, filenames) in os.walk(directory):
                    for filename in filenames:
                        if filename == request.DATA['template_name']:
                            with open(os.path.join(dirpath, filename), "r") as myfile:
                                soup = BeautifulSoup(myfile)
                                soup_elements = soup.find_all(request.DATA['tag'].lower())
                                if len(soup_elements) > 1:
                                    for element in soup_elements:
                                        if element.string:
                                            formatted_text = self.clean_text(element.string)
                                            if formatted_text == request.DATA['old_text']:
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
                                with open(os.path.join(dirpath, filename), "w") as myfile:
                                    myfile.write(html)
            self.post_save(self.object, created=True)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        self.object = serializer.save(force_update=True)
        self.post_save(self.object, created=False)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, *args, **kwargs):
        return self.update_or_create_pagelement(request, *args, **kwargs)


class FileUploadView(AccountMixin, APIView):
    parser_classes = (FileUploadParser,)

    def post(self, request, account_slug=None, format=None):#pylint: disable=unused-argument,redefined-builtin
        img = request.FILES['img']
        img_obj = UploadedImage(
            img=img,
            account=self.get_account()
            )

        serializer = UploadedImageSerializer(img_obj)
        serializer.save()
        response = {
            'img': os.path.join(settings.MEDIA_URL, serializer.data['img'])
            }
        return Response(response, status=status.HTTP_200_OK)
