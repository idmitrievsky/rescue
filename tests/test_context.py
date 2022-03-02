from contextlib import contextmanager
from typing import ContextManager, Generator

from rescue.core import bind, throw, unwrap
from rescue.util import Box, box_exc


@contextmanager
def trace_manager(
    enter_box: Box[bool], exit_box: Box[bool]
) -> Generator[None, None, None]:
    try:
        enter_box.content = True
        yield
    finally:
        exit_box.content = True


def throw_inside_context_manager(
    manager: ContextManager[None],
) -> Generator[ValueError, None, int]:
    with manager:
        yield from throw(ValueError("inside context manager"))
        return 0


def test_unwrap_context_manager_exit_on_err() -> None:
    a_default = 0
    exc_box: Box[ValueError] = Box()
    enter_box: Box[bool] = Box()
    exit_box: Box[bool] = Box()

    manager = trace_manager(enter_box, exit_box)
    thunk = throw_inside_context_manager(manager)

    unwrap(bind(thunk, box_exc(ValueError, exc_box, default=a_default)))

    assert enter_box.content
    assert exit_box.content
