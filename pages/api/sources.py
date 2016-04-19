# Copyright (c) 2016, Djaodjin Inc.
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
#pylint: disable=no-member

import logging, os, shutil

from django.template import TemplateSyntaxError
from django.template.defaultfilters import slugify
from django.template.loader import get_template
from django.utils._os import safe_join
from oslo_concurrency import lockutils
from rest_framework import status, generics, serializers
from rest_framework.response import Response

from .. import settings
from ..mixins import ThemePackageMixin


LOGGER = logging.getLogger(__name__)


class SourceCodeSerializer(serializers.Serializer):

    path = serializers.CharField(required=False, max_length=255)
    text = serializers.CharField(required=False, max_length=100000)

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class SourceDetailAPIView(ThemePackageMixin, generics.RetrieveUpdateAPIView):

    serializer_class = SourceCodeSerializer

    def _get_template_path(self, template=None):
        if template is None:
            template = get_template(self.kwargs.get('page'))
        try:
            return template.template.filename
        except AttributeError:
            return template.origin.name

    def retrieve(self, request, *args, **kwargs):
        with open(self._get_template_path()) as source_file:
            source_content = source_file.read()
        return Response({"path": self.kwargs.get('page'),
            "text": source_content})

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        template_path = self._get_template_path()
        if isinstance(settings.THEME_DIR_CALLABLE, basestring):
            from ..compat import import_string
            settings.THEME_DIR_CALLABLE = import_string(
                settings.THEME_DIR_CALLABLE)
        theme_base = settings.THEME_DIR_CALLABLE(self.account)
        if not template_path.startswith(theme_base):
            resp_status = status.HTTP_201_CREATED
            # XXX Until the whole theme feature is rewritten properly.
            default_template_path = template_path
            template_path = safe_join(theme_base, 'templates',
                self.kwargs.get('page'))
            if not os.path.isdir(os.path.dirname(template_path)):
                os.makedirs(os.path.dirname(template_path))
            shutil.copy(default_template_path, template_path)
        else:
            resp_status = status.HTTP_200_OK

        # We only write the file if the template syntax is correct.
        with lockutils.lock(slugify(template_path), lock_file_prefix="pages-"):
            backup_path = template_path + '~'
            shutil.copy(template_path, backup_path)
            with open(template_path, 'w') as source_file:
                source_file.write(serializer.validated_data['text'])
            try:
                template = get_template(self.kwargs.get('page'))
                assert self._get_template_path(template) == template_path
                LOGGER.info("Written to %s", template_path)
                os.remove(backup_path)
            except TemplateSyntaxError:
                os.remove(template_path)
                os.rename(backup_path, template_path)
                return self.retrieve(request, *args, **kwargs)
            return Response(serializer.data, status=resp_status)


