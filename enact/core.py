from typing import Generator, TypeVar

_ReturnType = TypeVar("_ReturnType")


def evaluate(
    partial_fn: Generator[None, None, _ReturnType],
) -> _ReturnType:
    try:
        next(partial_fn)
        raise AssertionError("argument doesn't yield")
    except StopIteration as _e:
        return _e.value
