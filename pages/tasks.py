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

import os

from celery import task
from pages.models import UploadedImage, PageElement
from pages.settings import MEDIA_PATH, NO_LOCAL_STORAGE
from django.conf import settings

# XXX -  not callable on pylint!
@task()#pylint: disable=not-callable
def upload_to_s3(uploaded_file, account, filename):
    if account:
        full_path = MEDIA_PATH + account.slug + '/' + filename
    else:
        full_path = MEDIA_PATH + filename
    if not NO_LOCAL_STORAGE:

        uploaded_temp = UploadedImage.objects.get(
            uploaded_file_temp=full_path)

        uploaded_temp.uploaded_file = uploaded_file
        uploaded_temp.save()

        page_elements = PageElement.objects.filter(text='/media/' + full_path)
        for page_element in page_elements:
            page_element.text = settings.S3_URL + '/' + full_path
            page_element.save()
        # delete file in server
        os.remove(os.path.join(settings.MEDIA_ROOT, full_path))
    else:
        img_obj = UploadedImage(
            uploaded_file=uploaded_file,
            account=account
            )
        img_obj.save()
        UploadedImage.objects.filter(
            uploaded_file=full_path).order_by('-created_at')[0].delete()
