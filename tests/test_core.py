# name of fn under test, context of test, desired result
from rescue.core import bind, exc_handler, unwrap, wrap_into_exc_handler
from rescue.util import Box, box_exc
from tests.exc import drop_exc_with_runtime_error_on_match, echo_even


def test_exc_handler_will_call_argument() -> None:
    call_count = 0

    @wrap_into_exc_handler(RuntimeError)
    def handler(_: RuntimeError) -> None:
        nonlocal call_count
        call_count += 1

    unwrap(handler(RuntimeError("check")))

    assert call_count == 1


def test_unwrap_on_err_handler_invocation() -> None:
    box: Box[ValueError] = Box()
    a_default = 0

    return_value = unwrap(
        bind(echo_even(1), box_exc(ValueError, box, default=a_default))
    )

    assert return_value == a_default
    assert isinstance(box.content, ValueError)


def test_bind_on_no_throw_return_value() -> None:
    box: Box[ValueError] = Box()
    a_default = -1

    value_err_handler = exc_handler(ValueError)(
        box_exc(ValueError, box, default=a_default)
    )

    thunk = echo_even(0)

    total_fn = bind(
        thunk,
        value_err_handler,
    )

    assert unwrap(total_fn) == 0
    assert box.content is None


def test_unwrap_on_handler_throw_invoke_appropriate_handler() -> None:
    a_default = 10
    ignored_default = 0

    box: Box[RuntimeError] = Box()
    runtime_err_handler = exc_handler(RuntimeError)(
        box_exc(RuntimeError, box, default=a_default)
    )

    handler = drop_exc_with_runtime_error_on_match(
        ValueError, "even number", ignored_default
    )

    assert unwrap(bind(bind(echo_even(1), handler), runtime_err_handler)) == a_default

    assert isinstance(box.content, RuntimeError)
    assert str(box.content) == "match pattern in error"
