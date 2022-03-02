from rescue.core import unwrap, wrap_into_exc_handler


def test_exc_handler_will_call_argument() -> None:
    call_count = 0

    @wrap_into_exc_handler(RuntimeError)
    def handler(_: RuntimeError) -> None:
        nonlocal call_count
        call_count += 1

    unwrap(handler(RuntimeError("check")))

    assert call_count == 1
