from contextlib import contextmanager
from typing import Callable, Generator, Type, TypeVar, Union

import pytest

from enact.exc import (
    ExceptionState,
    HandlerInvocation,
    can_handle,
    eval_with_handler,
    evaluate,
    try_eval,
    with_handler,
)
from example.exc import crush, echo_even, echo_even_number, throw_inside_context_manager
from example.mut import Cell

T = TypeVar("T")


def exc_saver(cell: Cell[T]) -> Callable[[T], None]:
    def write_exc_to_cell(exception: T) -> None:
        cell.content = exception

    return write_exc_to_cell


def test_throw_can_yield_once() -> None:
    partial_fn = crush()

    exc = next(partial_fn)

    assert isinstance(exc, RuntimeError)


def test_throw_can_yield_only_once() -> None:
    partial_fn = crush()

    next(partial_fn)

    with pytest.raises(AssertionError, match="throw interrupts execution"):
        next(partial_fn)


def test_try_eval_exception_return() -> None:
    odd_int = 1

    exc = try_eval(echo_even(odd_int))

    assert isinstance(exc, ValueError)


def test_try_eval_value_return() -> None:
    even_int = 2

    return_value = try_eval(echo_even(even_int))

    assert return_value == even_int


def test_can_handle_will_call_argument() -> None:
    call_count = 0

    def handler_fn(_: RuntimeError) -> None:
        nonlocal call_count
        call_count += 1

    handler = can_handle(RuntimeError)(handler_fn)

    handler(RuntimeError("check"))

    assert call_count == 1


def test_eval_with_handler_on_err_handler_invocation() -> None:
    exc_cell: Cell[ValueError] = Cell()

    return_value = eval_with_handler(echo_even(1), exc_saver(exc_cell))

    assert isinstance(return_value, HandlerInvocation)
    assert isinstance(exc_cell.content, ValueError)


def test_eval_with_handler_on_ok_return_value() -> None:
    even_int = 2
    exc_cell: Cell[ValueError] = Cell()

    return_value = eval_with_handler(echo_even(even_int), exc_saver(exc_cell))

    assert return_value == even_int
    assert exc_cell.content is None


@contextmanager
def trace_manager(
    enter_cell: Cell[bool], exit_cell: Cell[bool]
) -> Generator[None, None, None]:
    try:
        enter_cell.content = True
        yield
    finally:
        exit_cell.content = True


def test_eval_with_handler_context_manager_exit_on_err() -> None:
    exc_cell: Cell[ValueError] = Cell()
    enter_cell: Cell[bool] = Cell()
    exit_cell: Cell[bool] = Cell()

    manager = trace_manager(enter_cell, exit_cell)
    partial_fn = throw_inside_context_manager(manager)

    eval_with_handler(partial_fn, exc_saver(exc_cell))

    assert exit_cell.content


def test_handler_is_not_invoked_when_no_throw() -> None:
    type_err_cell: Cell[TypeError] = Cell()
    value_err_cell: Cell[ValueError] = Cell()

    type_err_handler = can_handle(TypeError)(exc_saver(type_err_cell))
    value_err_handler = can_handle(ValueError)(exc_saver(value_err_cell))

    partial_fn = echo_even_number(0)

    total_fn = with_handler(
        with_handler(
            partial_fn,
            type_err_handler,
        ),
        value_err_handler,
    )

    assert evaluate(total_fn) == 0
    assert type_err_cell.content is None
    assert value_err_cell.content is None


@pytest.mark.parametrize(
    "input_value, check_type_cell_content, check_value_cell_content, return_value_type",
    [
        ("str", True, None, HandlerInvocation),
        (1, None, True, HandlerInvocation),
    ],
)
def test_multiple_handlers(
    input_value: Union[int, str],
    check_type_cell_content: bool,
    check_value_cell_content: bool,
    return_value_type: Type[ExceptionState],
) -> None:
    type_err_cell: Cell[TypeError] = Cell()
    value_err_cell: Cell[ValueError] = Cell()

    type_err_handler = can_handle(TypeError)(exc_saver(type_err_cell))
    value_err_handler = can_handle(ValueError)(exc_saver(value_err_cell))

    partial_fn = echo_even_number(input_value)

    total_fn = with_handler(
        with_handler(
            partial_fn,
            type_err_handler,
        ),
        value_err_handler,
    )

    assert isinstance(evaluate(total_fn), return_value_type)

    if check_type_cell_content:
        assert isinstance(type_err_cell.content, type_err_handler.exc_type)
    else:
        assert type_err_cell.content is None

    if check_value_cell_content:
        assert isinstance(value_err_cell.content, value_err_handler.exc_type)
    else:
        assert value_err_cell.content is None
