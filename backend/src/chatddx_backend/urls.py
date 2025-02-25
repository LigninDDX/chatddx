from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.http import HttpResponse
from django.urls import include, path


def auth_check(request):
    if request.user.is_authenticated:
        return HttpResponse(status=200)
    else:
        return HttpResponse(status=401)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("chatddx_backend.api.urls")),
    path("auth/", auth_check, name="auth_check"),
]
urlpatterns += i18n_patterns(path("cms/", include("chatddx_backend.cms.urls")))
urlpatterns += staticfiles_urlpatterns()
