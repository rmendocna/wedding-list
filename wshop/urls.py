from django.contrib import admin
from django.urls import include, path

from glist import urls as gl_urls

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', include(gl_urls))
]
