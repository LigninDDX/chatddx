from collections import OrderedDict
from typing import TypeVar, cast

from chatddx_backend.agents import type_map
from chatddx_backend.agents.trail import TrailModel, TrailSpec
from chatddx_backend.agents.trail.spec_loader import model_from_pk

T = TypeVar("T", bound=TrailSpec)


class TrailCache:
    cache: OrderedDict[tuple[type[TrailSpec], int], TrailSpec]

    def __init__(self, max_size: int):
        self.max_size = max_size
        self.cache = OrderedDict()

    async def get_instance(self, Spec: type[T], pk: int) -> T:
        Model = type_map.resolve(Spec, TrailModel)
        key = (Spec, pk)

        if key in self.cache:
            self.cache.move_to_end(key)
            return cast(T, self.cache[key])

        spec = Spec.model_validate(await model_from_pk(Model, pk))

        self.cache[key] = spec

        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)

        return spec


trail_cache = TrailCache(max_size=100)
