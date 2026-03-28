from collections import OrderedDict
from typing import TypeVar, cast

from chatddx_backend.agents import type_map
from chatddx_backend.agents.trail import TrailModel, TrailSpec

T = TypeVar("T", bound=TrailSpec)


class TrailCache:
    cache: OrderedDict[tuple[type[TrailSpec], int], TrailSpec]

    def __init__(self, max_size: int):
        self.max_size = max_size

        self.cache = OrderedDict()

    def get_instance(self, Spec: type[T], pk: int) -> T:
        Model = type_map.resolve(Spec, TrailModel)
        key = (Spec, pk)

        if key in self.cache:
            self.cache.move_to_end(key)
            return cast(T, self.cache[key])

        spec = Spec.model_validate(Model.objects.get(pk=pk))

        self.cache[key] = spec

        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)

        return spec


trail_cache = TrailCache(max_size=100)
