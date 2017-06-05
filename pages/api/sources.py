# Copyright (c) 2017, Djaodjin Inc.
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

import logging, os, tempfile, sys

from django.template import TemplateSyntaxError
from django.template.loader import _engine_list, get_template
from django.template.backends.jinja2 import get_exception_info
from django.utils import six
from django.utils._os import safe_join
import jinja2
from rest_framework import status, generics, serializers
from rest_framework.response import Response

from ..mixins import ThemePackageMixin
from ..themes import get_theme_dir


LOGGER = logging.getLogger(__name__)


def check_template(template_source, using=None):
    """
    Loads and returns a template for the given name.

    Raises TemplateDoesNotExist if no such template exists.
    """
    errs = {}
    engines = _engine_list(using)
    # We should find at least one engine that does not raise an error.
    for engine in engines:
        try:
            try:
                return engine.from_string(template_source)
            except jinja2.TemplateSyntaxError as exc:
                new = TemplateSyntaxError(exc.args)
                new.template_debug = get_exception_info(exc)
                six.reraise(TemplateSyntaxError, new, sys.exc_info()[2])
        except TemplateSyntaxError as err:
            errs.update({engine: err})
    if errs:
        raise TemplateSyntaxError(errs)


def get_template_path(template=None, relative_path=None):
    if template is None:
        template = get_template(relative_path)
    try:
        return template.template.filename
    except AttributeError:
        return template.origin.name


def write_template(template_path, template_source):
    check_template(template_source)
    base_dir = os.path.dirname(template_path)
    if not os.path.isdir(base_dir):
        os.makedirs(base_dir)
    temp_file = tempfile.NamedTemporaryFile(
        mode='w+t', dir=base_dir, delete=False)
    temp_file.write(template_source)
    temp_file.close()
    os.rename(temp_file.name, template_path)
    LOGGER.info("pid %d wrote to %s", os.getpid(), template_path)


class SourceCodeSerializer(serializers.Serializer):

    path = serializers.CharField(required=False, max_length=255)
    text = serializers.CharField(required=False, max_length=100000)

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class SourceDetailAPIView(ThemePackageMixin, generics.RetrieveUpdateAPIView,
                          generics.CreateAPIView):

    serializer_class = SourceCodeSerializer

    def retrieve(self, request, *args, **kwargs):
        relative_path = self.kwargs.get('page')
        with open(get_template_path(
                relative_path=relative_path)) as source_file:
            source_content = source_file.read()
        return Response({"path": relative_path, "text": source_content})

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        relative_path = self.kwargs.get('page')
        template_path = get_template_path(relative_path=relative_path)
        theme_base = get_theme_dir(self.account)
        if not template_path.startswith(theme_base):
            resp_status = status.HTTP_201_CREATED
            template_path = safe_join(theme_base, 'templates', relative_path)
        else:
            resp_status = status.HTTP_200_OK

        # We only write the file if the template syntax is correct.
        try:
            write_template(template_path, serializer.validated_data['text'])
        except TemplateSyntaxError as err:
            LOGGER.debug("%s", err, extra={'request': request})
            return self.retrieve(request, *args, **kwargs)
        return Response(serializer.data, status=resp_status)

    def perform_create(self, serializer): #pylint:disable=unused-argument
        relative_path = self.kwargs.get('page')
        theme_base = get_theme_dir(self.account)
        template_path = safe_join(theme_base, 'templates', relative_path)
        write_template(template_path, '''{% extends "base.html" %}

{% block content %}
<h1>Lorem Ipsum</h1>
{% endblock %}
''')
