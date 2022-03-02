from typing import Generator, Type, TypeVar

from rescue.core import ExcHandler, exc_handler, throw


def echo_even(x: int) -> Generator[ValueError, None, int]:
    if x % 2 != 0:
        yield from throw(ValueError("x must be an even number"))
    return x


E = TypeVar("E", bound=Exception)
T = TypeVar("T")


def drop_exc_with_runtime_error_on_match(
    exc_type: Type[E], pattern: str, default: T
) -> ExcHandler[E, RuntimeError, T]:
    @exc_handler(exc_type)
    def handler(exc: E) -> Generator[RuntimeError, None, T]:
        if pattern in str(exc):
            yield from throw(RuntimeError("match pattern in error"))
        return default

    return handler
