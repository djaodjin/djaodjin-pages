# Copyright (c) 2021, Djaodjin Inc.
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
from __future__ import unicode_literals

import logging, os, subprocess, tempfile

from bs4 import BeautifulSoup
from django.conf import settings as django_settings
from django.http import Http404
from django.template.base import TemplateSyntaxError
from django.template.backends.jinja2 import Jinja2 as Jinja2Templates
from django.template.loader import _engine_list
from django.utils.encoding import force_text
from django.utils._os import safe_join
from jinja2.lexer import Lexer
from rest_framework import status, generics
from rest_framework.response import Response

from ..compat import DebugLexer, TokenType, get_html_engine, six
from ..mixins import ThemePackageMixin, UpdateEditableMixin
from ..themes import check_template, get_theme_dir, get_template_path
from ..serializers import SourceCodeSerializer, SourceElementSerializer

LOGGER = logging.getLogger(__name__)

STATE_DIRECTIVE_BEGIN = 1
STATE_BLOCK_BEGIN = 2
STATE_BLOCK_CONTENT = 3
STATE_BLOCK_CONTENT_ESCAPE = 4

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


class SourceEditAPIView(ThemePackageMixin, UpdateEditableMixin,
                        generics.GenericAPIView):

    serializer_class = SourceElementSerializer

    def put(self, request, *args, **kwargs):
        """
        Updates an element inside a template source file

        **Examples

        .. code-block:: http

            PUT /api/themes/sources/editables/heading HTTP/1.1

        .. code-block:: json

             {
               "text": "New heading",
               "hints": [{
                 "index": 0,
                 "name": "index.html"
               }, {
                 "index": 1,
                 "name": "base.html"
               }]
             }

        responds

        .. code-block:: json

             {
               "text": "New heading"
             }
        """
        return self.update(request, *args, **kwargs)

    @staticmethod
    def tokens_as_text(buffered_tokens):
        block_text = ""
        for tok in buffered_tokens:
            token_value = tok.contents
            if tok.token_type == TokenType.BLOCK:
                block_text += "{%% %s %%}" % token_value
            elif tok.token_type == TokenType.VAR:
                block_text += "{{%s}}" % token_value
            else:
                block_text += token_value
        return block_text


    def update_block(self, element_id, element_text, block_text, dest,
                     template_path=None):
        #pylint:disable=too-many-arguments
        LOGGER.debug("%slooking for element id='%s' in '%s'",
            "(%s) " % template_path if template_path else "",
            element_id, block_text)
        soup = BeautifulSoup(block_text, 'html5lib')
        editable = soup.find(id=element_id)
        if editable:
            if 'edit-formatted' in editable['class']:
                self.insert_formatted(editable, element_text)
            elif 'edit-markdown' in editable['class']:
                self.insert_markdown(editable, element_text)
            elif 'edit-currency' in editable['class']:
                self.insert_currency(editable, element_text)
            elif 'droppable-image' in editable['class']:
                editable['src'] = element_text
            else:
                editable.string = element_text
            # Implementation Note:
            # 1. we have to use ``.body.next`` here
            #    because html5lib "fixes" our HTML by adding missing
            #    html/body tags.
            # 2. str(soup) instead of soup.prettify() to avoid
            #    trailing whitespace on a reformatted HTML textarea
            body_text = str(soup.body.next)
            if six.PY2 and hasattr(body_text, 'decode'):
                body_text = body_text.decode('utf-8')
            dest.write("\n%s\n" % body_text)
        else:
            if six.PY2 and hasattr(block_text, 'decode'):
                block_text = block_text.decode('utf-8')
            dest.write(block_text)

    def update(self, request, *args, **kwargs):
        #pylint:disable=unused-argument,unused-variable
        #pylint:disable=too-many-locals,too-many-nested-blocks
        #pylint:disable=too-many-statements
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        element_id = self.kwargs.get('path')
        element_text = serializer.validated_data.get('text')
        hints = serializer.validated_data.get('hints', [])
        LOGGER.debug("update '%s' with \"%s\" (hints=%s)",
            element_id, element_text, hints)
        found = False
        dest = None
        dest_hint = None
        for hint in hints:
            relative_path = hint.get('name')
            template_path = get_template_path(relative_path=relative_path)
            dest = six.StringIO()
            dest_hint = hint
            dest_path = template_path
            theme_base = get_theme_dir(self.theme)
            if not template_path.startswith(theme_base):
                resp_status = status.HTTP_201_CREATED
                dest_path = safe_join(
                    theme_base, 'templates', relative_path)
            else:
                resp_status = status.HTTP_200_OK

            LOGGER.info("searching for %s in %s ...", element_id, template_path)
            with open(template_path) as template_file:
                template_string = template_file.read()
            try:
                template_string = force_text(template_string)
                engine, unused_libraries, unused_builtins = get_html_engine()
                buffered_tokens = []
                block_depth = 0
                state = None
                if isinstance(engine, Jinja2Templates):
                    template_name = None
                    tokens = Lexer(engine.env).tokeniter(template_string,
                        template_name, filename=template_path)
                    escaped_tokens = []
                    for token in tokens:
                        LOGGER.debug("block_depth=%d state=%s token=%s",
                            block_depth, state, token)
                        token_type = token[1]
                        token_value = token[2]
                        if six.PY2 and hasattr(token_value, 'encode'):
                            token_value = token_value.encode('utf-8')
                        if state is None:
                            if token_type == 'block_begin':
                                state = STATE_DIRECTIVE_BEGIN
                            dest.write(str(token_value))
                        elif state == STATE_DIRECTIVE_BEGIN:
                            if token_type == 'block_end':
                                state = None
                            elif (token_type == 'name' and
                                  token_value == 'block'):
                                state = STATE_BLOCK_BEGIN
                                block_depth = block_depth + 1
                            dest.write(str(token_value))
                        elif state == STATE_BLOCK_BEGIN:
                            if token_type == 'block_end':
                                state = STATE_BLOCK_CONTENT
                            dest.write(str(token_value))
                        elif state == STATE_BLOCK_CONTENT:
                            if token_type == 'block_begin':
                                state = STATE_BLOCK_CONTENT_ESCAPE
                                escaped_tokens = [token]
                            else:
                                buffered_tokens += [token]
                        elif state == STATE_BLOCK_CONTENT_ESCAPE:
                            escaped_tokens += [token]
                            if token_type == 'block_end':
                                buffered_tokens += escaped_tokens
                                escaped_tokens = []
                                state = STATE_BLOCK_CONTENT
                            elif (token_type == 'name' and
                                  token_value == 'block'):
                                block_depth = block_depth + 1
                                buffered_tokens += escaped_tokens
                                escaped_tokens = []
                                state = STATE_BLOCK_CONTENT
                            elif (token_type == 'name' and
                                  token_value == 'endblock'):
                                block_depth = block_depth - 1
                                if block_depth:
                                    buffered_tokens += escaped_tokens
                                    escaped_tokens = []
                                    state = STATE_BLOCK_CONTENT
                                else:
                                    state = None
                                    if buffered_tokens:
                                        block_text = "%s" % ''.join([
                                            tok[2] for tok in buffered_tokens])
                                        self.update_block(
                                            element_id, element_text,
                                            block_text, dest,
                                            template_path=template_path)
                                        buffered_tokens = []
                                    if escaped_tokens:
                                        dest.write("%s" % ''.join([tok[2]
                                            for tok in escaped_tokens]))
                                        escaped_tokens = []
                    if buffered_tokens:
                        block_text = "%s" % ''.join([
                            tok[2] for tok in buffered_tokens])
                        self.update_block(
                            element_id, element_text,
                            block_text, dest,
                            template_path=template_path)
                        buffered_tokens = []
                    if escaped_tokens:
                        dest.write("%s" % ''.join([
                            tok[2] for tok in escaped_tokens]))
                        escaped_tokens = []
                    dest.write("\n")
                else:
                    # DjangoTemplates
                    lexer = DebugLexer(template_string)
                    state = None
                    for token in lexer.tokenize():
                        LOGGER.debug("block_depth=%d state=%s token=%s",
                            block_depth, state, token)
                        token_value = token.contents
                        if six.PY2 and hasattr(token_value, 'encode'):
                            token_value = token_value.encode('utf-8')
                        if state is None:
                            if token.token_type == TokenType.BLOCK:
                                if token.contents.startswith('block'):
                                    block_depth = block_depth + 1
                                    state = STATE_BLOCK_CONTENT
                                dest.write("{%% %s %%}" % token_value)
                            elif token.token_type == TokenType.VAR:
                                dest.write("{{%s}}" % token_value)
                            else:
                                dest.write(str(token_value))
                        elif state == STATE_BLOCK_CONTENT:
                            if token.token_type == TokenType.BLOCK:
                                if token.contents.startswith('block'):
                                    block_depth = block_depth + 1
                                    buffered_tokens += [token]
                                elif token.contents.startswith('endblock'):
                                    block_depth = block_depth - 1
                                    if block_depth:
                                        buffered_tokens += [token]
                                    else:
                                        if buffered_tokens:
                                            block_text = self.tokens_as_text(
                                                buffered_tokens)
                                            self.update_block(
                                                element_id, element_text,
                                                block_text, dest,
                                                template_path=template_path)
                                            buffered_tokens = []
                                        dest.write("{%% %s %%}" % token_value)
                                        state = None
                                else:
                                    buffered_tokens += [token]
                            else:
                                buffered_tokens += [token]

                    if buffered_tokens:
                        block_text = self.tokens_as_text(buffered_tokens)
                        self.update_block(
                            element_id, element_text,
                            block_text, dest,
                            template_path=template_path)
                        buffered_tokens = []

            except UnicodeDecodeError:
                LOGGER.warning("%s: Templates can only be constructed "
                    "from unicode or UTF-8 strings.", template_path)
            dest = dest.getvalue()
            if dest and dest != template_string:
                block_text = dest
                if six.PY2 and hasattr(block_text, 'encode'):
                    block_text = block_text.encode('utf-8')
                if not os.path.exists(os.path.dirname(dest_path)):
                    os.makedirs(os.path.dirname(dest_path))
                with open(dest_path, 'w') as dest_file:
                    dest_file.write(block_text)
                if django_settings.DEBUG:
                    try:
                        cmdline = ['diff', '-u', template_path, dest_path]
                        LOGGER.info(' '.join(cmdline))
                        LOGGER.info(subprocess.check_output(cmdline))
                    except subprocess.CalledProcessError:
                        pass
                found = True
                break
        if not found:
            raise Http404()

        # clear template loaders caches
        engines = _engine_list(using=None)
        for engine in engines:
            try:
                engine.env.cache.clear()
            except AttributeError:
                pass

        return Response(self.get_serializer().to_representation({
                'text': dest,
                'hints': [dest_hint]
            }), status=resp_status)


class SourceEditBaseAPIView(SourceEditAPIView):
    """
    To prevent duplicate operationId when generating documentation.
    """
    schema = None



class SourceDetailAPIView(ThemePackageMixin, generics.RetrieveUpdateAPIView,
                          generics.CreateAPIView):
    """
    Retrieves a template source file

    **Examples

    .. code-block:: http

        GET /api/themes/sources/index.html HTTP/1.1

    responds

    .. code-block:: json

         {
           "text": "..."
         }
    """
    serializer_class = SourceCodeSerializer

    def post(self, request, *args, **kwargs):
        """
        Creates a template source file

        **Examples

        .. code-block:: http

            POST /api/themes/sources/index.html HTTP/1.1

        .. code-block:: json

             {
               "text": "..."
             }

        responds

        .. code-block:: json

             {
               "text": "..."
             }
        """
        #pylint:disable=useless-super-delegation
        return super(SourceDetailAPIView, self).post(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        """
        Updates a template source file

        **Examples

        .. code-block:: http

            PUT /api/themes/sources/index.html HTTP/1.1

        .. code-block:: json

             {
               "text": "..."
             }

        responds

        .. code-block:: json

             {
               "text": "..."
             }
        """
        #pylint:disable=useless-super-delegation
        return super(SourceDetailAPIView, self).put(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        relative_path = self.kwargs.get('page')
        with open(get_template_path(
                relative_path=relative_path)) as source_file:
            source_content = source_file.read()
        return Response({'path': relative_path, 'text': source_content})

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        relative_path = self.kwargs.get('page')
        template_path = get_template_path(relative_path=relative_path)
        theme_base = get_theme_dir(self.theme)
        if not template_path.startswith(theme_base):
            resp_status = status.HTTP_201_CREATED
            template_path = safe_join(theme_base, 'templates', relative_path)
        else:
            resp_status = status.HTTP_200_OK

        # We only write the file if the template syntax is correct.
        try:
            write_template(template_path, serializer.validated_data['text'])

            # clear template loaders caches
            engines = _engine_list(using=None)
            for engine in engines:
                try:
                    engine.env.cache.clear()
                except AttributeError:
                    pass

        except TemplateSyntaxError as err:
            LOGGER.debug("%s", err, extra={'request': request})
            return self.retrieve(request, *args, **kwargs)
        return Response(serializer.data, status=resp_status)

    def perform_create(self, serializer): #pylint:disable=unused-argument
        relative_path = self.kwargs.get('page')
        theme_base = get_theme_dir(self.theme)
        template_path = safe_join(theme_base, 'templates', relative_path)
        write_template(template_path, '''{% extends "base.html" %}

{% block content %}
<h1>Lorem Ipsum</h1>
{% endblock %}
''')
