from django.conf.urls import url

from WebEMEP.views import proxy

urlpatterns = [
    url(r'^emep_proxy/(?P<information>\w+)', proxy, name="EMEP_Proxy"),
]