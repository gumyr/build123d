

from typing import Any, Callable, Generic, Optional, Type, TypeVar


ClassPropertyType = TypeVar("ClassPropertyType")

class classproperty():
    def __init__(self, method: Callable[[ClassPropertyType], ClassPropertyType]):
        self.fget = method

    def __get__(self, instance: Any, cls: ClassPropertyType) -> ClassPropertyType:
        return self.fget(cls)

    def getter(self, method):
        self.fget = method
        return self
