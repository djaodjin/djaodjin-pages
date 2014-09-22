from django.db import models

class ExampleAccount(models.Model):

    slug = models.SlugField()
    name = models.CharField(max_length=50)

    def __unicode__(self):
        return self.slug

