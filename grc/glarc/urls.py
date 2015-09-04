from django.conf.urls import patterns, url
from glarc import views

urlpatterns = patterns('',
        url(r'^$', views.index, name='index'),
        url(r'^about/$', views.about, name='about'),
        url(r'^get_json/$', views.get_json, name='get_json'),
        url(r'^shortest_path/$', views.shortest_path, name='shortest_path'),
        url(r'single_author/$', views.single_author, name='single_author'),
        url(r'longest_path/$', views.longest_path, name='longest_path'),
        url(r'kw_search/$', views.kw_search, name='kw_search'),
        )