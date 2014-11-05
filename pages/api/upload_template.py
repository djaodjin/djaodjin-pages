#pylint: disable=no-init,no-member,unused-variable
#pylint: disable=old-style-class,line-too-long,maybe-no-member

import os
import zipfile, tempfile, shutil


from django.utils import timezone

from rest_framework import status
from rest_framework.views import APIView
from rest_framework import generics
from rest_framework.parsers import FileUploadParser
from rest_framework.response import Response

from pages.models import UploadedTemplate
from pages.serializers import UploadedTemplateSerializer


from pages.settings import UPLOADED_TEMPLATE_DIR, UPLOADED_STATIC_DIR

from pages.mixins import AccountMixin

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
