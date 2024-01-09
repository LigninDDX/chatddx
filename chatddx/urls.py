from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("gpt/", include ("gpt.urls")),
    path("admin/", admin.site.urls),
]