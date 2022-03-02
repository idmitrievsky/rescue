import functools
import sys
from contextlib import closing
from typing import Callable, Generator, Generic, NoReturn, Type, TypeVar, Union, cast

_ExceptionType = TypeVar("_ExceptionType", bound=Exception)
_OptionalExceptionType = TypeVar("_OptionalExceptionType", bound=Union[Exception, None])
_ReturnType = TypeVar("_ReturnType")

HandlerCallable = Callable[
    [_ExceptionType], Generator[_OptionalExceptionType, None, _ReturnType]
]


def throw(exception: _ExceptionType) -> Generator[_ExceptionType, None, NoReturn]:
    yield exception
    # `yield from` should respect `NoReturn` annotation, but doesn't
    raise AssertionError("throw interrupts execution")


class ExcHandler(Generic[_ExceptionType, _OptionalExceptionType, _ReturnType]):
    def __init__(
        self,
        exc_type: Type[_ExceptionType],
        handler: HandlerCallable[_ExceptionType, _OptionalExceptionType, _ReturnType],
    ):
        self.exc_type = exc_type
        self.handler = handler

    def __call__(
        self, exception: _ExceptionType
    ) -> Generator[_OptionalExceptionType, None, _ReturnType]:
        return self.handler(exception)


def exc_handler(
    exc_type: Type[_ExceptionType],
) -> Callable[
    [
        HandlerCallable[_ExceptionType, _OptionalExceptionType, _ReturnType],
    ],
    ExcHandler[_ExceptionType, _OptionalExceptionType, _ReturnType],
]:
    def decorator(
        handler: HandlerCallable[_ExceptionType, _OptionalExceptionType, _ReturnType],
    ) -> ExcHandler[_ExceptionType, _OptionalExceptionType, _ReturnType]:
        return ExcHandler(
            exc_type,
            handler,
        )

    return decorator


def wrap(
    fn: Callable[[_ExceptionType], _ReturnType]
) -> Callable[[_ExceptionType], Generator[None, None, _ReturnType]]:
    @functools.wraps(fn)
    def handler(exc: _ExceptionType) -> Generator[None, None, _ReturnType]:
        always_false = False
        if always_false:
            yield None
        return fn(exc)

    return handler


def wrap_into_exc_handler(
    exc_type: Type[_ExceptionType],
) -> Callable[
    [Callable[[_ExceptionType], _ReturnType]],
    ExcHandler[_ExceptionType, None, _ReturnType],
]:
    def decorator(
        handler: Callable[[_ExceptionType], _ReturnType],
    ) -> ExcHandler[_ExceptionType, None, _ReturnType]:
        return ExcHandler(
            exc_type,
            wrap(handler),
        )

    return decorator


def bind(
    gtr: Generator[Exception, None, _ReturnType],
    on_exc: ExcHandler[_ExceptionType, _OptionalExceptionType, _ReturnType],
) -> Generator[Exception, None, _ReturnType]:
    try:
        yielded_value = gtr.send(None)
    except StopIteration as _e:
        return _e.value

    exc_type = on_exc.exc_type
    target_gtr = gtr
    was_handler_invoked = False

    while True:
        try:
            # transfer control to the caller
            # receive the value if the caller decided to send a value in
            if isinstance(yielded_value, exc_type) and not was_handler_invoked:
                was_handler_invoked = True
                with closing(gtr):
                    handler_gtr = on_exc(yielded_value)
                    target_gtr = handler_gtr  # type: ignore

                    try:
                        yielded_value = cast(Exception, handler_gtr.send(None))
                    except StopIteration as _e:
                        return _e.value

            sent_value = yield yielded_value
        except GeneratorExit as _e:
            # if the caller decided to close us, close `gtr` first
            gtr.close()
            raise _e
        except BaseException:  # noqa: PIE786
            # if the caller decided to throw an exception
            exc_info = sys.exc_info()
            try:
                # throw the exception into `fn`
                # at this point it can yield another value
                # return a value by raising stop iteration
                # or raise exception that we should not handle
                yielded_value = gtr.throw(*exc_info)
            except StopIteration as _e:
                return_value = _e.value
                break
        else:
            try:
                yielded_value = target_gtr.send(sent_value)
            except StopIteration as _e:
                return _e.value

    return return_value


def unwrap(
    gtr: Generator[None, None, _ReturnType],
) -> _ReturnType:
    try:
        next(gtr)
        raise AssertionError("argument doesn't yield")
    except StopIteration as _e:
        return _e.value
