from django.contrib import admin
from django.urls import include, path

from glist import urls as gl_urls

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include(gl_urls))
]
