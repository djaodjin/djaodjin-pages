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

from django.db import models
from django.core.files.storage import FileSystemStorage

from . import settings

FILE_SYSTEM = FileSystemStorage(location=settings.MEDIA_ROOT)


class UploadedImage(models.Model):
    """
    Image uploaded
    """
    created_at = models.DateTimeField(auto_now_add=True)
    uploaded_file = models.CharField(
        max_length=500, null=True, blank=True)
    uploaded_file_cache = models.CharField(
        max_length=500, null=True, blank=True)
    account = models.ForeignKey(
       settings.ACCOUNT_MODEL, related_name='media_uploads',
       null=True, blank=True)
    # Original filename to make search easier.
    file_name = models.CharField(max_length=100)
    tags = models.CharField(max_length=200, blank=True, null=True)

    def __unicode__(self):
        return unicode(self.get_src_file())

    def get_src_file(self):
        if self.uploaded_file:
            return self.uploaded_file
        else:
            return self.uploaded_file_cache

    def get_sha1(self):
        """
        Return the sha1 name of the file without extension
        Will be used as id to update and delete file
        """
        src = self.get_src_file()
        if src:
            return os.path.splitext(os.path.basename(self.get_src_file()))[0]
        return '*unkown*'

    def relative_path(self):
        return self.uploaded_file_cache.replace(settings.MEDIA_URL, '')


class PageElement(models.Model):
    """
    Elements of an editable HTML page.
    """

    slug = models.CharField(max_length=50)
    text = models.TextField(blank=True)
    image = models.ForeignKey(UploadedImage, null=True)
    account = models.ForeignKey(
        settings.ACCOUNT_MODEL, related_name='account_page_element', null=True)

    def __unicode__(self):
        return unicode(self.slug)


class UploadedTemplate(models.Model):
    """
    This model allow to record uploaded template.
    """

    account = models.ForeignKey(
        settings.ACCOUNT_MODEL,
        related_name='account_template', null=True, blank=True)
    name = models.CharField(max_length=150)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=False)

    def __unicode__(self):
        if self.account:
            return '%s-%s' % (self.account, self.name)
        else:
            return self.name
