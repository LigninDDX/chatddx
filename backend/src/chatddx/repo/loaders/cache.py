# src/chatddx/repo/loaders/cache.py
from collections import OrderedDict
from typing import cast

from asgiref.sync import async_to_sync

from chatddx.repo.base import TrailModel, TrailSpec
from chatddx.repo.main import Repo


class TrailCache:
    cache: OrderedDict[tuple[type[TrailSpec], int], TrailSpec]
    max_size: int

    def __init__(self, max_size: int):
        self.max_size = max_size
        self.cache = OrderedDict()

    def get_sync[T: TrailSpec](self, Spec: type[T], pk: int) -> T:
        return async_to_sync(self.get_async)(Spec, pk)

    async def get_async[T: TrailSpec](self, Spec: type[T], pk: int) -> T:
        Model = Repo(Spec, TrailModel)
        key = (Spec, pk)

        if key in self.cache:
            self.cache.move_to_end(key)
            return cast(T, self.cache[key])

        spec = Spec.model_validate(await Model.objects.aget(pk=pk))

        self.cache[key] = spec

        if len(self.cache) > self.max_size:
            _ = self.cache.popitem(last=False)

        return spec


trail_cache = TrailCache(max_size=100)
