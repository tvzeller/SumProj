from django.conf.urls import patterns, url
from glarc import views

urlpatterns = patterns('',
        url(r'^$', views.index, name='index'),
        url(r'^about/$', views.about, name='about'),
        url(r'^get_json/$', views.get_json, name='get_json')
        )