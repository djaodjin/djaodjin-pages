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


import os
import zipfile, tempfile, shutil

from django.db.models import Q
from django.utils import timezone

from rest_framework import status, generics
from rest_framework.parsers import FileUploadParser
from rest_framework.response import Response

from pages.models import UploadedTemplate
from pages.serializers import UploadedTemplateSerializer
from pages.settings import (
    UPLOADED_TEMPLATE_DIR,
    UPLOADED_STATIC_DIR,
    DISABLE_ACCOUNT_TEMPLATE_PATH)

from pages.mixins import AccountMixin

class UploadedTemplateListAPIView(AccountMixin, generics.ListCreateAPIView):
    serializer_class = UploadedTemplateSerializer
    parser_classes = (FileUploadParser,)

    def get_queryset(self):
        queryset = UploadedTemplate.objects.filter(
            Q(account=self.get_account())|Q(account=None))
        return queryset

    def post(self, request, format=None, *args, **kwargs):
        #pylint: disable=unused-argument,redefined-builtin
        #pylint: disable=too-many-locals,too-many-statements
        new_package = True
        account = self.get_account()
        if account and not DISABLE_ACCOUNT_TEMPLATE_PATH:
            uploaded_template_dir = os.path.join(
                UPLOADED_TEMPLATE_DIR, account.slug)
            uploaded_static_dir = os.path.join(
                UPLOADED_STATIC_DIR, account.slug)
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
                            if not name.endswith('.css') \
                                and not name.endswith('.js')\
                                and not name.endswith('.css.map')\
                                and not name.endswith('.png'):
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
        return Response(serializer.data, status=200)


class UploadedTemplateAPIView(AccountMixin, generics.RetrieveUpdateAPIView):
    serializer_class = UploadedTemplateSerializer
    model = UploadedTemplate

