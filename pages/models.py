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

from django.db import models
from pages.settings import (
    MEDIA_PATH,
    ACCOUNT_MODEL,
    DEFAULT_STORAGE_BUCKET_NAME,
    USE_S3)

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

def file_name(instance, filename):
    path = MEDIA_PATH
    if instance.account:
        return path + instance.account.slug + '/' + filename
    else:
        return path + filename


class PageElement(models.Model):
    """
    Elements of an editable HTML page.
    """

    slug = models.CharField(max_length=50)
    text = models.TextField(blank=True)
    account = models.ForeignKey(
        ACCOUNT_MODEL, related_name='account_page_element', null=True)

    def __unicode__(self):
        return unicode(self.slug)


from django.core.files.storage import FileSystemStorage
from storages.backends.s3boto import S3BotoStorage

FILE_SYSTEM = FileSystemStorage(location=settings.MEDIA_ROOT)


class S3Bucket(models.Model):
    bucket_name = models.CharField(max_length=150)
    account = models.ForeignKey(
        ACCOUNT_MODEL, related_name='bucket_account', null=True, blank=True)


class UploadedImage(models.Model):
    """
   	Image uploaded
    """
    created_at = models.DateTimeField(auto_now_add=True)
    uploaded_file = models.FileField(upload_to=file_name, storage=None, null=True, blank=True)
    uploaded_file_temp = models.FileField(
        upload_to=file_name, storage=FILE_SYSTEM, null=True, blank=True)
    account = models.ForeignKey(
        ACCOUNT_MODEL, related_name='account_image', null=True, blank=True)
    tags = models.CharField(max_length=200, blank=True, null=True)

    def __unicode__(self):
        return unicode(self.uploaded_file)

    def save(self, *args, **kwargs):
        if self.uploaded_file and USE_S3:
            if self.account:
                try:
                    bucket = S3Bucket.objects.get(account=self.account)
                    self.uploaded_file.storage = S3BotoStorage(
                        bucket=bucket.bucket_name)
                except S3Bucket.DoesNotExist:
                    raise ImproperlyConfigured(
                        "Account '%s' has not valid S3 bucket" \
                        % self.account.slug)
            else:
                self.uploaded_file.storage = S3BotoStorage(
                    bucket=DEFAULT_STORAGE_BUCKET_NAME)
        super(UploadedImage, self).save(*args, **kwargs)


class UploadedTemplate(models.Model):
    """
    This model allow to record uploaded template.
    """

    account = models.ForeignKey(
        ACCOUNT_MODEL,
        related_name='account_template', null=True, blank=True)
    name = models.CharField(max_length=150)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField()
    is_active = models.BooleanField(default=False)

    def __unicode__(self):
        if self.account:
            return '%s-%s' % (self.account, self.name)
        else:
            return self.name


