from chatddx_backend.api import views
from django.urls import path

urlpatterns = [
    path("chat/clusters/<str:cluster>", views.chat_cluster, name="chat_cluster"),
    path("chat/history", views.chat_history, name="chat_history"),
]
