# Copyright (c) 2015, DjaoDjin inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
# TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from django.core.files.storage import get_storage_class
from storages.backends.s3boto import S3BotoStorage
from django.core.exceptions import ImproperlyConfigured

from .settings import (
    GET_CURRENT_ACCOUNT,
    ACCOUNT_URL_KWARG,
    AWS_STORAGE_BUCKET_NAME)
from .compat import import_string


class AccountMixin(object):

    account_url_kwarg = ACCOUNT_URL_KWARG

    def get_account(self):
        if GET_CURRENT_ACCOUNT:
            return import_string(GET_CURRENT_ACCOUNT)(
                self.account_url_kwarg, self.kwargs)
        return None


class UploadedImageMixin(object):

    @staticmethod
    def get_default_storage(instance):
        if get_storage_class() == S3BotoStorage:
            if instance.account:
                try:
                    bucket_name = instance.account.bucket_name
                except AttributeError:
                    raise ImproperlyConfigured(
                        "Your account model need to have a bucket name field.")
            else:
                bucket_name = AWS_STORAGE_BUCKET_NAME
            return get_storage_class()(bucket=bucket_name)
        else:
            return None
