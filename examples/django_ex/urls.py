from django.conf.urls.defaults import patterns, include, url

urlpatterns = patterns('',
    url(r'^$', 'django_ex.views.example_view', name='example_view'),
)
