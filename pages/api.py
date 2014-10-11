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
import zipfile, tempfile, shutil

from bs4 import BeautifulSoup

from django.utils import timezone
from django.conf import settings
from django.core.files.storage import default_storage

from rest_framework import status
from rest_framework.views import APIView
from rest_framework import generics
from rest_framework.parsers import FileUploadParser
from rest_framework.response import Response
from rest_framework.serializers import ValidationError
from rest_framework.views import APIView

from pages.models import PageElement, UploadedImage, UploadedTemplate
from pages.serializers import (
    PageElementSerializer,
    UploadedImageSerializer,
    UploadedTemplateSerializer)

from .settings import (
    IMG_PATH,
    UPLOADED_TEMPLATE_DIR,
    UPLOADED_STATIC_DIR)

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
            template_name = request.DATA['template_name']
            template_path = request.DATA['template_path']
            if template_name:
                for directory in settings.TEMPLATE_DIRS:
                    for (dirpath, dirnames, filenames) in os.walk(directory):
                        for filename in filenames:
                            if filename == request.DATA['template_name']:
                                path = os.path.join(dirpath, filename)
            elif template_path:
                path = template_path
            self.write_html(path, new_id)
            self.post_save(self.object, created=True)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        self.object = serializer.save(force_update=True)
        self.post_save(self.object, created=False)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, *args, **kwargs):
        return self.update_or_create_pagelement(request, *args, **kwargs)

import hashlib
class FileUploadView(AccountMixin, APIView):
    parser_classes = (FileUploadParser,)

    def post(self, request, account_slug=None, format=None):#pylint: disable=unused-argument,redefined-builtin
        img = request.FILES['img']
        existing_file = False
        sha1_filename = hashlib.sha1(img.read()).hexdigest() + '.' + str(img).split('.')[1]
        if settings.USE_S3:
            path = IMG_PATH
            if self.get_account():
                full_path = path + self.get_account().slug + '/' + sha1_filename
            else:
                full_path = path + sha1_filename

            if default_storage.exists(full_path):
                existing_file = True
        if not existing_file:
            img_obj = UploadedImage(
                img=img,
                account=self.get_account()
                )
            serializer = UploadedImageSerializer(img_obj)
            serializer.save()
        else:
            img_obj = UploadedImage.objects.get(img=full_path)
            serializer = UploadedImageSerializer(img_obj)

        response = {
            'img': os.path.join(settings.MEDIA_URL, serializer.data['img'])
            }
        return Response(response, status=status.HTTP_200_OK)


class UploadedTemplateListAPIView(AccountMixin, generics.ListCreateAPIView):
    serializer_class = UploadedTemplateSerializer

    def get_queryset(self):
        queryset = UploadedTemplate.objects.filter(
            account=self.get_account())
        return queryset


class TemplateUploadView(AccountMixin, APIView):
    parser_classes = (FileUploadParser,)

    def post(self, request, format=None, *args, **kwargs):#pylint: disable=unused-argument, redefined-builtin, too-many-locals, too-many-statements

        new_package = True
        account = self.get_account()
        if account:
            uploaded_template_dir = os.path.join(UPLOADED_TEMPLATE_DIR, account.slug)
            uploaded_static_dir = os.path.join(UPLOADED_STATIC_DIR, account.slug)
        else:
            uploaded_template_dir = UPLOADED_TEMPLATE_DIR
            uploaded_static_dir = UPLOADED_STATIC_DIR
        file_obj = request.FILES['file']
        # zfile = zipfile.ZipFile(file_obj)

        if zipfile.is_zipfile(file_obj):
            zfile = zipfile.ZipFile(file_obj)
        else:
            return Response({'info': "Invalid zipfile"},
                status=status.HTTP_400_BAD_REQUEST)

        root_path = str(file_obj).replace('.zip', '')
        root_path_templates = str(file_obj).replace('.zip', '/templates/')
        root_path_static = str(file_obj).replace('.zip', '/static/')

        if os.path.exists(
            os.path.join(uploaded_template_dir, root_path)):
            new_package = False

        dir_temp = os.path.join(tempfile.gettempdir(), root_path)
        if not os.path.exists(dir_temp):
            os.makedirs(dir_temp)

        temp_dir_templates = os.path.join(dir_temp, 'templates')
        if not os.path.exists(temp_dir_templates):
            os.makedirs(temp_dir_templates)

        temp_dir_static = os.path.join(dir_temp, 'static')
        if not os.path.exists(temp_dir_static):
            os.makedirs(temp_dir_static)

        members = zfile.namelist()
        templates_to_extract = [m for m in members\
            if m.startswith(root_path_templates) and m != root_path_templates]
        static_to_extract = [m for m in members\
            if m.startswith(root_path_static) and m != root_path_static]

        print static_to_extract
        print templates_to_extract
        for name in zfile.namelist():
            # remove __MACOSX File and DS_Store
            if name.startswith('/'):
                shutil.rmtree(dir_temp)
                return Response("Invalid zipfile",
                    status=status.HTTP_400_BAD_REQUEST)

            if not "__MACOSX" in name and not ".DS_Store" in name:
                if name in templates_to_extract or name in static_to_extract:
                    if name in templates_to_extract:
                        is_template = True
                        directory = temp_dir_templates
                    elif name in static_to_extract:
                        is_template = False
                        directory = temp_dir_static

                    if is_template:
                        new_name = name.replace('%s/templates/' % root_path, '')
                    else:
                        new_name = name.replace('%s/static/' % root_path, '')

                    if str(name).endswith('/'):
                        os.makedirs(os.path.join(directory, new_name))
                    else:
                        if is_template:
                            if not name.endswith(('.html', '.jinja2')):
                                shutil.rmtree(dir_temp)
                                return Response(
                                    "Templates directory has to \
                                    contain only html or jinja2 file",
                                    status=status.HTTP_403_FORBIDDEN)
                        else:
                            print name.endswith('.css')
                            print name.endswith('.js')
                            if not name.endswith('.css') \
                                and not name.endswith('.js'):
                                shutil.rmtree(dir_temp)
                                return Response(
                                    "Static directory has to \
                                    contains only css or js file",
                                    status=status.HTTP_403_FORBIDDEN)
                        outfile = open(os.path.join(directory, new_name), 'wb')
                        outfile.write(zfile.read(name))
                        outfile.close()

        if os.path.exists(
            os.path.join(uploaded_template_dir, root_path)):
            shutil.rmtree(
                os.path.join(uploaded_template_dir, root_path))

        shutil.move(
            temp_dir_templates,
            os.path.join(uploaded_template_dir, root_path))

        if os.path.exists(
            os.path.join(uploaded_static_dir, root_path)):

            shutil.rmtree(
                os.path.join(uploaded_static_dir, root_path))

        if os.listdir(temp_dir_static):
            shutil.move(
                temp_dir_static,
                os.path.join(uploaded_static_dir, root_path))

        # delete temp directory
        shutil.rmtree(dir_temp)
        
        if new_package:
            template_package = UploadedTemplate(account=account,
                name=root_path.replace('/', ''))
            template_package.updated_at = timezone.now()
            template_package.save()
        else:
            template_package = UploadedTemplate.objects.get(
                account=account,
                name=root_path.replace('/', ''))
            template_package.updated_at = timezone.now()
            template_package.save()
        serializer = UploadedTemplateSerializer(template_package)
        return Response(serializer.data, status=200) #pylint: disable=no-member

