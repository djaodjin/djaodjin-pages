from django.conf.urls import patterns, url
from pages.api import PageElementDetail
# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    url(r'^editables/(?P<slug>[\w-]+)/',
    	PageElementDetail.as_view(), name='edit_page_element'),
)
