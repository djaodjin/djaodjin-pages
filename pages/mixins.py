# Copyright (c) 2014, DjaoDjin inc.
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

import os
from django.db.models.loading import get_model
from django.shortcuts import get_object_or_404
from pages.models import UploadedTemplate
from .settings import ACCOUNT_URL_KWARG, ACCOUNT_MODEL
from django.conf import settings
class AccountMixin(object):

    account_url_kwarg = ACCOUNT_URL_KWARG

    def get_account(self):
        print 'hrere'
        if isinstance(ACCOUNT_MODEL, str):
            account_model = get_model(*ACCOUNT_MODEL.rsplit('.', 1))
        else:
            account_model = ACCOUNT_MODEL
        print self.kwargs.get(self.account_url_kwarg)
        if self.account_url_kwarg in self.kwargs and\
            self.kwargs.get(self.account_url_kwarg) is not None:
            return get_object_or_404(account_model,
                slug=self.kwargs.get(self.account_url_kwarg))
        return None

class TemplateChoiceMixin(AccountMixin):

    def get_template_names(self):
        """
        Returns a list of template names to be used for the request. Must return
        a list. May not be called if render_to_response is overridden.
        """
        account = self.get_account()
        print account
        if self.template_name is None:
            raise ImproperlyConfigured(
                "TemplateResponseMixin requires either a definition of "
                "'template_name' or an implementation of 'get_template_names()'")
        else:
            if account:
                template_name = None
                uploaded_templates = UploadedTemplate.objects.filter(account=account).order_by("-created_at")[0]
                root_account_path = account.slug +'/'+ uploaded_templates.name
                for directory in settings.TEMPLATE_DIRS:
                    for (dirpath, dirnames, filenames) in os.walk(directory):
                        if root_account_path in dirpath:
                            for filename in filenames:
                                if filename == self.template_name:
                                    template_name = os.path.join(root_account_path, filename)

                if template_name:
                    return [template_name]
                else:
                    return [self.template_name]
            else:
                return [self.template_name]
