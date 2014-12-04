from django.conf.urls import patterns, include, url
from django.contrib import admin
from testsite.views import HomeView
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = patterns('',
    url(r'^', include('pages.urls')),
    url(r'^$', HomeView.as_view()),

    url(r'^admin/', include(admin.site.urls)),
)+ static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)\
+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
