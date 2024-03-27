from enum import Enum, unique
from typing import Callable, NamedTuple
from functools import wraps, lru_cache


@unique
class CycleStage(Enum):
    NONE = 0
    LOADED = 1
    UNLOADED = 2


class Listener(NamedTuple):
    fn: Callable
    allow_life_cycle_kwarg: bool
    include_result: bool


class Notify:
    def __init__(self, cb: Callable, stage: CycleStage, life_cycle_key="life_cycle"):
        self.cb = cb
        self.listeners = []
        self.stage = stage
        self.life_cycle_key = life_cycle_key

    def notify(self, allow_life_cycle_kwarg=True, include_result=False):
        def decorator(fn: Callable):
            @wraps(fn)
            def wrapper(*args, **kwargs):
                return fn(*args, **kwargs)

            self.listeners.append(Listener(wrapper, allow_life_cycle_kwarg, include_result))
            return wrapper

        return decorator

    def __call__(self, *args, **kwargs):
        res = self.cb(*args, **kwargs)
        for fn, allow_life_cycle_kwarg, include_result in self.listeners:
            kw = {}
            if allow_life_cycle_kwarg:
                kw[self.life_cycle_key] = self.stage
            if include_result:
                kw["result"] = res
            fn(**kw)
        self.listeners.clear()


def lifecycle(stage: CycleStage):
    def decorator(fn: Callable):
        # the use of lru_cache is to ensure the function is called at most once
        # it is flexible enough to allow calling more than once if the args change
        @lru_cache
        @wraps(fn)
        def wrapper(*args, **kwargs):
            return fn(*args, **kwargs)

        return Notify(wrapper, stage)

    return decorator
