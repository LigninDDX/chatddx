from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path
from django.conf.urls.i18n import i18n_patterns

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
]
urlpatterns += i18n_patterns(
    path("cms/", include("cms.urls"))
)
urlpatterns += staticfiles_urlpatterns()
