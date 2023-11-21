# Copyright (c) 2023, Djaodjin Inc.
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

"""
Command to extract text from either an uploaded document
or a Google Docs link to set as a PageElement's text.
"""
import logging

import os
import re
import zipfile
from io import BytesIO
from xml.etree.ElementTree import XML, ParseError

import requests
from django.core.management.base import BaseCommand, CommandError

from ...models import PageElement

LOGGER = logging.getLogger(__name__)


WORD_NAMESPACE = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
PARA = WORD_NAMESPACE + 'p'
TEXT = WORD_NAMESPACE + 't'

class Command(BaseCommand):
    help = 'Uploads a .docx file from a local system or Google Drive link'

    def add_arguments(self, parser):
        parser.add_argument(
            'source',
            type=str,
            help='Source ("upload" for local file, "drive" for Google Drive link)')
        parser.add_argument(
            'identifier',
            type=str,
            help='File path or Google Drive link')
        parser.add_argument(
            'page_element_slug',
            type=str,
            help='Slug of the PageElement to update')

    @staticmethod
    def format_drive_url(url):
        if 'docs.google.com/document' not in url:
            raise CommandError(f'Invalid Google Docs URL: "{url}"')

        match = re.search(r'/d/([0-9A-Za-z_-]{28,})/', url)
        if not match:
            raise CommandError(f'Could not extract document ID from Google Docs URL: "{url}"')

        doc_id = match.group(1)
        return f'https://docs.google.com/document/d/{doc_id}/export?format=docx'

    @staticmethod
    def get_docx_text(file_obj):
        try:
            with zipfile.ZipFile(file_obj) as document:
                xml_content = document.read('word/document.xml')
        except zipfile.BadZipFile:
            raise CommandError(
                'The file is not a valid zipfile (possibly not a docx).')

        try:
            tree = XML(xml_content)
        except ParseError:
            raise CommandError(
                'There is an error parsing the document XML.')

        paragraphs = []
        for paragraph in tree.iter(PARA):
            texts = [node.text for node in paragraph.iter(TEXT) if node.text]
            if texts:
                paragraphs.append(''.join(texts))

        return '\n\n'.join(paragraphs)

    def handle(self, *args, **options):
        source = options['source']
        identifier = options['identifier']
        slug = options['page_element_slug']

        if source not in ['upload', 'drive']:
            self.stdout.write(f'Invalid source "{source}". Source must be either "upload" or "drive".')
            return

        if source == 'upload':
            if not os.path.exists(identifier):
                self.stdout.write(f"File {identifier} does not exist")
                return
            with open(identifier, 'rb') as file_obj:
                text = self.get_docx_text(file_obj)
        else:
            try:
                drive_url = self.format_drive_url(identifier)
            except ValueError as e:
                self.stdout.write(str(e))
                return

            try:
                response = requests.get(drive_url)
                response.raise_for_status()
                text = self.get_docx_text(BytesIO(response.content))
            except requests.RequestException as e:
                self.stdout.write(f"Failed to retrieve the document from Google Drive. "
                                  "Please make sure the Doc linked is public.")
                return

        try:
            page_element = PageElement.objects.get(slug=slug)
            page_element.text = text
            page_element.save()
            self.stdout.write(f'Successfully updated PageElement with slug "{slug}"')
        except PageElement.DoesNotExist:
            self.stdout.write(f'PageElement with slug "{slug}" does not exist. No update was made.')
