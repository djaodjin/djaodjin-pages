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

import logging, random

from django.db import IntegrityError, models, transaction
from django.template.defaultfilters import slugify
from rest_framework.exceptions import ValidationError

from . import settings


LOGGER = logging.getLogger(__name__)


class RelationShip(models.Model):
    orig_element = models.ForeignKey(
        "PageElement", related_name='from_element')
    dest_element = models.ForeignKey(
        "PageElement", related_name='to_element')
    tag = models.SlugField(null=True)

    def __unicode__(self):
        return "%s to %s" % (
            self.orig_element.slug, self.dest_element.slug) #pylint: disable=no-member

class PageElement(models.Model):
    """
    Elements of an editable HTML page.
    """

    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=150, blank=True)
    text = models.TextField(blank=True)
    account = models.ForeignKey(
        settings.ACCOUNT_MODEL, related_name='account_page_element', null=True)
    relationships = models.ManyToManyField("self",
        related_name='related_to', through='RelationShip', symmetrical=False)
    tag = models.SlugField(null=True, blank=True)

    def __unicode__(self):
        return self.slug

    def add_relationship(self, element, tag=None):
        return RelationShip.objects.get_or_create(
            orig_element=self, dest_element=element,
            defaults={'tag': tag})

    def remove_relationship(self, element):
        RelationShip.objects.filter(
            orig_element=self,
            dest_element=element).delete()
        return True

    def get_relationships(self, tag=None):
        if not tag:
            return self.relationships.filter(
                to_element__orig_element=self)
        else:
            return self.relationships.filter(
                to_element__tag=tag,
                to_element__orig_element=self)

    def get_related_to(self, tag):
        return self.related_to.filter(
            from_element__tag=tag,
            from_element__dest_element=self)

    def save(self, force_insert=False, force_update=False,
             using=None, update_fields=None):
        if self.slug: # serializer will set created slug to '' instead of None.
            return super(PageElement, self).save(
                force_insert=force_insert, force_update=force_update,
                using=using, update_fields=update_fields)
        max_length = self._meta.get_field('slug').max_length
        slug_base = slugify(self.title)
        if len(slug_base) > max_length:
            slug_base = slug_base[:max_length]
        self.slug = slug_base
        for _ in range(1, 10):
            try:
                with transaction.atomic():
                    return super(PageElement, self).save(
                        force_insert=force_insert, force_update=force_update,
                        using=using, update_fields=update_fields)
            except IntegrityError, err:
                if 'uniq' not in str(err).lower():
                    raise
                suffix = '-%s' % "".join([random.choice("abcdef0123456789")
                    for _ in range(7)])
                if len(slug_base) + len(suffix) > max_length:
                    self.slug = slug_base[:(max_length - len(suffix))] + suffix
                else:
                    self.slug = slug_base + suffix
        raise ValidationError({'detail':
            "Unable to create a unique URL slug from title '%s'" % self.title})


class MediaTag(models.Model):

    location = models.CharField(max_length=250)
    tag = models.CharField(max_length=50)

    def __unicode__(self):
        return unicode(self.tag)


class LessVariable(models.Model):
    """
    This model stores value of a variable used to generate a css file.
    """
    name = models.CharField(max_length=250)
    value = models.CharField(max_length=250)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    account = models.ForeignKey(settings.ACCOUNT_MODEL,
        related_name='account_less_variable', null=True)
    cssfile = models.CharField(max_length=50)

    class Meta:
        unique_together = ('account', 'cssfile', 'name')

    def __unicode__(self):
        return '%s: %s' % (self.name, self.value)


class ThemePackage(models.Model):
    """
    This model allow to record uploaded template.
    """
    slug = models.SlugField(unique=True)
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


def get_active_theme():
    """
    Returns the active theme from a request.
    """
    if settings.ACTIVE_THEME_CALLABLE:
        from .compat import import_string  # Because AppRegistryNotReady
        theme_slug = import_string(settings.ACTIVE_THEME_CALLABLE)()
        LOGGER.debug("pages: get_active_theme('%s')", theme_slug)
        try:
            return ThemePackage.objects.get(slug=theme_slug)
        except ThemePackage.DoesNotExist:
            pass
    return None

