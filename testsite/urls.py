from django.conf.urls import patterns, include, url
from django.contrib import admin
from testsite.views import HomeView, UploadedTemplatesView
from django.conf.urls.static import static
from django.conf import settings
from pages.settings import SLUG_RE

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'testsite.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    url(r'^uploaded-templates/', UploadedTemplatesView.as_view()),
    url(r'^(?:(?P<account_slug>%s)/)?' % SLUG_RE, include('pages.urls')),
    url(r'^(?:(?P<account_slug>%s)/)?$' % SLUG_RE, HomeView.as_view()),
    url(r'^get-progress/upload/', 'pages.api.upload_progress'),

    url(r'^admin/', include(admin.site.urls)),
)+ static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)\
+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
