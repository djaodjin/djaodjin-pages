from django.conf.urls import patterns, include, url
from django.contrib import admin
from testsite.views import HomeView
from django.conf.urls.static import static
from django.conf import settings
from pages.settings import SLUG_RE

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'testsite.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    url(r'^(?P<organization>%s)/' % SLUG_RE, include('pages.urls')),
    url(r'^$',HomeView.as_view()),
    url(r'^admin/', include(admin.site.urls)),
)+ static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
