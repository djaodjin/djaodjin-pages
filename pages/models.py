from django.db import models
from django.contrib import admin
# Create your models here.

class PageElement(models.Model):
    """
    Elements of an editable HTML page.
    """

    slug = models.CharField(max_length=50)
    text = models.TextField(blank=True)

    def __unicode__(self):
        return unicode(self.slug)

admin.site.register(PageElement)
