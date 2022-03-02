from typing import Generator, Union

from rescue.core import bind, exc_handler, throw, unwrap
from rescue.util import Box, box_exc


def echo_even_number(
    x: Union[int, str]
) -> Generator[Union[ValueError, TypeError], None, int]:
    if isinstance(x, str):
        yield from throw(TypeError("x must be a number"))

    assert not isinstance(x, str)

    if x % 2 != 0:
        yield from throw(ValueError("x must be an even number"))

    return x


def test_bind_composition_on_error_throw_invoke_bound_handler() -> None:
    type_err_box: Box[TypeError] = Box()
    value_err_box: Box[ValueError] = Box()

    input_value = "str"
    a_default = 0
    another_default = 2

    type_err_handler = exc_handler(TypeError)(
        box_exc(TypeError, type_err_box, default=a_default)
    )
    value_err_handler = exc_handler(ValueError)(
        box_exc(ValueError, value_err_box, default=another_default)
    )

    thunk = echo_even_number(input_value)

    total_fn = bind(
        bind(
            thunk,
            type_err_handler,
        ),
        value_err_handler,
    )

    assert unwrap(total_fn) == a_default
    assert isinstance(type_err_box.content, type_err_handler.exc_type)
    assert value_err_box.content is None


def test_bind_composition_on_value_throw_invoke_value_handler() -> None:
    type_err_box: Box[TypeError] = Box()
    value_err_box: Box[ValueError] = Box()

    input_value = 1
    a_default = 0
    another_default = 2

    type_err_handler = exc_handler(TypeError)(
        box_exc(TypeError, type_err_box, default=another_default)
    )
    value_err_handler = exc_handler(ValueError)(
        box_exc(ValueError, value_err_box, default=a_default)
    )

    thunk = echo_even_number(input_value)

    total_fn = bind(
        bind(
            thunk,
            type_err_handler,
        ),
        value_err_handler,
    )

    assert unwrap(total_fn) == a_default
    assert isinstance(value_err_box.content, value_err_handler.exc_type)
    assert type_err_box.content is None
