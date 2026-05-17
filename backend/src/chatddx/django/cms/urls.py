from chatddx_backend.cms import views
from django.urls import path

urlpatterns = [
    path("assistant", views.assistant, name="assistant"),
]
