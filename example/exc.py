from typing import ContextManager, Type, TypeVar, Union

from enact.exc import (
    ExcHandlerWithFx,
    ReturnWithFx,
    eval_with_exc_handler,
    exc_handler,
    exc_handler_with_fx,
    throw,
)
from example.mut import Cell


def crush() -> ReturnWithFx[RuntimeError, int]:
    yield from throw(RuntimeError("not ok"))
    return 0


def echo_even(x: int) -> ReturnWithFx[ValueError, int]:
    if x % 2 != 0:
        yield from throw(ValueError("x must be an even number"))
    return x


def throw_inside_context_manager(
    manager: ContextManager[None],
) -> ReturnWithFx[ValueError, int]:
    with manager:
        yield from throw(ValueError("inside context manager"))
        return 0


def echo_even_number(
    x: Union[int, str]
) -> ReturnWithFx[Union[ValueError, TypeError], int]:
    if isinstance(x, str):
        yield from throw(TypeError("x must be a number"))

    assert not isinstance(x, str)

    if x % 2 != 0:
        yield from throw(ValueError("x must be an even number"))

    return x


def increment_cell(cell: Cell[int], bound: int) -> ReturnWithFx[ValueError, None]:
    assert cell.content is not None, "no such cell"

    if cell.content + 1 >= bound:
        yield from throw(ValueError("cell is already full"))
    cell.content += 1


def fill_cell(count: int, bound: int) -> int:
    cell: Cell[int] = Cell(content=0)

    @exc_handler(ValueError)
    def set_zero(_: ValueError) -> None:
        cell.content = 0

    for _ in range(count):
        partial_fn = increment_cell(cell, bound)
        eval_with_exc_handler(partial_fn, set_zero)
        if cell.content == 0:
            break

    assert cell.content is not None, "no such cell"
    return cell.content


E = TypeVar("E", bound=Exception)
T = TypeVar("T")


def drop_exc_with_runtime_error_on_match(
    exc_type: Type[E], pattern: str, default: T
) -> ExcHandlerWithFx[E, RuntimeError, T]:
    @exc_handler_with_fx(exc_type)
    def handler(exc: E) -> ReturnWithFx[RuntimeError, T]:
        if pattern in str(exc):
            yield from throw(RuntimeError("match pattern in error"))
        return default

    return handler
