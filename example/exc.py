from typing import ContextManager, Union

from enact.exc import PartialFn, can_except, eval_with_except, throw
from example.mut import Cell


def crush() -> PartialFn[RuntimeError, int]:
    yield from throw(RuntimeError("not ok"))
    return 0


def echo_even(x: int) -> PartialFn[ValueError, int]:
    if x % 2 != 0:
        yield from throw(ValueError("x must be an even number"))
    return x


def throw_inside_context_manager(
    manager: ContextManager[None],
) -> PartialFn[ValueError, int]:
    with manager:
        yield from throw(ValueError("inside context manager"))
        return 0


def echo_even_number(
    x: Union[int, str]
) -> PartialFn[Union[ValueError, TypeError], int]:
    if isinstance(x, str):
        yield from throw(TypeError("x must be a number"))

    assert not isinstance(x, str)

    if x % 2 != 0:
        yield from throw(ValueError("x must be an even number"))

    return x


def increment_cell(cell: Cell[int], bound: int) -> PartialFn[ValueError, None]:
    assert cell.content is not None, "no such cell"

    if cell.content + 1 >= bound:
        yield from throw(ValueError("cell is already full"))
    cell.content += 1


def fill_cell(count: int, bound: int) -> int:
    cell: Cell[int] = Cell(content=0)

    @can_except(ValueError)
    def set_zero(_: ValueError) -> None:
        cell.content = 0

    for _ in range(count):
        partial_fn = increment_cell(cell, bound)
        eval_with_except(partial_fn, set_zero)
        if cell.content == 0:
            break

    assert cell.content is not None, "no such cell"
    return cell.content
