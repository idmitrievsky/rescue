from contextlib import contextmanager
from typing import Callable, Generator, TypeVar

import pytest

from enact.core import evaluate
from enact.exc import eval_with_exc_handler, exc_handler, try_eval, with_handler
from example.exc import (
    crush,
    drop_exc_with_runtime_error_on_match,
    echo_even,
    echo_even_number,
    throw_inside_context_manager,
)
from example.mut import Cell

T = TypeVar("T")
R = TypeVar("R")


def exc_saver(cell: Cell[T], default: R) -> Callable[[T], R]:
    def write_exc_to_cell(exception: T) -> R:
        cell.content = exception
        return default

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


def test_total_exc_handler_will_call_argument() -> None:
    call_count = 0

    def handler_fn(_: RuntimeError) -> None:
        nonlocal call_count
        call_count += 1

    handler = exc_handler(RuntimeError)(handler_fn)

    handler(RuntimeError("check"))

    assert call_count == 1


def test_eval_with_handler_on_err_handler_invocation() -> None:
    exc_cell: Cell[ValueError] = Cell()
    a_default = 0

    return_value = eval_with_exc_handler(
        echo_even(1), exc_saver(exc_cell, default=a_default)
    )

    assert return_value == a_default
    assert isinstance(exc_cell.content, ValueError)


def test_eval_with_handler_on_ok_return_value() -> None:
    even_int = 2
    a_default = 0
    exc_cell: Cell[ValueError] = Cell()

    return_value = eval_with_exc_handler(
        echo_even(even_int), exc_saver(exc_cell, default=a_default)
    )

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
    a_default = 0
    exc_cell: Cell[ValueError] = Cell()
    enter_cell: Cell[bool] = Cell()
    exit_cell: Cell[bool] = Cell()

    manager = trace_manager(enter_cell, exit_cell)
    partial_fn = throw_inside_context_manager(manager)

    eval_with_exc_handler(partial_fn, exc_saver(exc_cell, default=a_default))

    assert exit_cell.content


def test_with_handler_on_no_throw_return_value() -> None:
    value_err_cell: Cell[ValueError] = Cell()
    a_default = -1

    value_err_handler = exc_handler(ValueError)(
        exc_saver(value_err_cell, default=a_default)
    )

    partial_fn = echo_even(0)

    total_fn = with_handler(
        partial_fn,
        value_err_handler,
    )

    assert evaluate(total_fn) == 0
    assert value_err_cell.content is None


def test_with_handler_composition_on_type_throw_invoke_type_handler() -> None:
    type_err_cell: Cell[TypeError] = Cell()
    value_err_cell: Cell[ValueError] = Cell()

    input_value = "str"
    a_default = 0
    another_default = 2

    type_err_handler = exc_handler(TypeError)(
        exc_saver(type_err_cell, default=a_default)
    )
    value_err_handler = exc_handler(ValueError)(
        exc_saver(value_err_cell, default=another_default)
    )

    partial_fn = echo_even_number(input_value)

    total_fn = with_handler(
        with_handler(
            partial_fn,
            type_err_handler,
        ),
        value_err_handler,
    )

    assert evaluate(total_fn) == a_default
    assert isinstance(type_err_cell.content, type_err_handler.exc_type)
    assert value_err_cell.content is None


def test_with_handler_composition_on_value_throw_invoke_value_handler() -> None:
    type_err_cell: Cell[TypeError] = Cell()
    value_err_cell: Cell[ValueError] = Cell()

    input_value = 1
    a_default = 0
    another_default = 2

    type_err_handler = exc_handler(TypeError)(
        exc_saver(type_err_cell, default=another_default)
    )
    value_err_handler = exc_handler(ValueError)(
        exc_saver(value_err_cell, default=a_default)
    )

    partial_fn = echo_even_number(input_value)

    total_fn = with_handler(
        with_handler(
            partial_fn,
            type_err_handler,
        ),
        value_err_handler,
    )

    assert evaluate(total_fn) == a_default
    assert isinstance(value_err_cell.content, value_err_handler.exc_type)
    assert type_err_cell.content is None


def test_with_handler_on_partial_handler_throw_invoke_next_handler() -> None:
    a_default = 10
    ignored_default = 0

    runtime_err_cell: Cell[RuntimeError] = Cell()
    runtime_err_handler = exc_handler(RuntimeError)(
        exc_saver(runtime_err_cell, default=a_default)
    )

    handler = drop_exc_with_runtime_error_on_match(
        ValueError, "even number", ignored_default
    )

    assert (
        evaluate(with_handler(with_handler(echo_even(1), handler), runtime_err_handler))
        == a_default
    )

    assert isinstance(runtime_err_cell.content, RuntimeError)
    assert str(runtime_err_cell.content) == "match pattern in error"


def test_with_handler_on_partial_handler_return_value() -> None:
    a_default = 10

    handler = drop_exc_with_runtime_error_on_match(ValueError, "nothing", a_default)

    assert try_eval(with_handler(echo_even(1), handler)) == a_default
