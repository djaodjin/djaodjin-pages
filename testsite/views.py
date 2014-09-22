# Create your views here.
from django.views.generic import TemplateView
from pages.views import PageView

class HomeView(PageView):
	template_name = "index.html"
