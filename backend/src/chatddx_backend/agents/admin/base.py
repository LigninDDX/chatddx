# src/chatddx_backend/agents/admin/base.py
from typing import Generic, TypeVar, cast

from django.db.models import Model as DjangoModel
from django.db.models import QuerySet
from django.http import HttpRequest
from unfold.admin import ModelAdmin

from chatddx_backend.agents.trail import TrailModel

T = TypeVar("T", bound="DjangoModel")


class TypedModelAdmin(ModelAdmin, Generic[T]):
    def get_queryset(self, request: HttpRequest) -> QuerySet[T]:
        return cast(QuerySet[T], super().get_queryset(request))


S = TypeVar("S", bound="TrailModel")


class TrailModelAdmin(TypedModelAdmin[S]):
    def get_queryset(self, request: HttpRequest) -> QuerySet[S]:
        qs: QuerySet[S] = super().get_queryset(request)
        return qs
