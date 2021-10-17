from typing import Generator, TypeVar

from enact.fx import Effect

T = TypeVar("T")


class Ask(Effect[T]):
    pass


def answer_two(_ask: Ask[int]) -> Generator[int, None, None]:
    yield 2


def add(x: int) -> Generator[Ask[int], int, int]:
    y = yield from Ask[int]().perform()
    return x + y
