from django.urls import path
from . import views

urlpatterns = [
    path("chat/clusters/<str:cluster>", views.chat_cluster, name="chat_cluster"),
]
