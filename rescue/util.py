from dataclasses import dataclass
from typing import Generic, Optional, Type, TypeVar

from rescue.core import ExcHandler, wrap_into_exc_handler

T = TypeVar("T")
E = TypeVar("E", bound=Exception)
R = TypeVar("R")


@dataclass
class Box(Generic[T]):
    content: Optional[T] = None


def box_exc(exc_type: Type[E], box: Box[E], default: R) -> ExcHandler[E, None, R]:
    def _write_exc_to_box(exception: E) -> R:
        box.content = exception
        return default

    return wrap_into_exc_handler(exc_type)(_write_exc_to_box)
