from dataclasses import dataclass
from typing import Generic, Optional, TypeVar

T = TypeVar("T")


@dataclass
class Cell(Generic[T]):
    content: Optional[T] = None
