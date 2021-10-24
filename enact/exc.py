import sys
from contextlib import closing
from typing import Callable, Generator, Generic, NoReturn, Type, TypeVar, Union

_ExceptionType = TypeVar("_ExceptionType", bound=Exception)
_HandlerExceptionType = TypeVar("_HandlerExceptionType", bound=Exception)
_ReturnType = TypeVar("_ReturnType")

PartialFn = Generator[_ExceptionType, None, _ReturnType]


def throw(exception: _ExceptionType) -> Generator[_ExceptionType, None, NoReturn]:
    yield exception
    # seems like `yield from` doesn't respect `NoReturn` annotation
    raise AssertionError("throw interrupts execution")


def try_eval(
    partial_fn: PartialFn[_ExceptionType, _ReturnType],
) -> Union[_ExceptionType, _ReturnType]:
    try:
        return next(partial_fn)
    except StopIteration as _e:
        return _e.value


class _TotalExcHandler(Generic[_ExceptionType, _ReturnType]):
    def __init__(
        self,
        exc_type: Type[_ExceptionType],
        except_fn: Callable[[_ExceptionType], _ReturnType],
    ):
        self.exc_type = exc_type
        self.except_fn = except_fn

    def __call__(self, exception: _ExceptionType) -> _ReturnType:
        return self.except_fn(exception)


class _PartialExcHandler(Generic[_ExceptionType, _HandlerExceptionType, _ReturnType]):
    def __init__(
        self,
        exc_type: Type[_ExceptionType],
        except_fn: Callable[
            [_ExceptionType], Generator[_HandlerExceptionType, None, _ReturnType]
        ],
    ):
        self.exc_type = exc_type
        self.except_fn = except_fn

    def __call__(
        self, exception: _ExceptionType
    ) -> Generator[_HandlerExceptionType, None, _ReturnType]:
        return self.except_fn(exception)


def total_exc_handler(
    exc_type: Type[_ExceptionType],
) -> Callable[
    [Callable[[_ExceptionType], _ReturnType]],
    _TotalExcHandler[_ExceptionType, _ReturnType],
]:
    def decorator(
        except_fn: Callable[[_ExceptionType], _ReturnType]
    ) -> _TotalExcHandler[_ExceptionType, _ReturnType]:
        return _TotalExcHandler(exc_type, except_fn)

    return decorator


def partial_exc_handler(
    exc_type: Type[_ExceptionType],
) -> Callable[
    [Callable[[_ExceptionType], Generator[_HandlerExceptionType, None, _ReturnType]]],
    _PartialExcHandler[_ExceptionType, _HandlerExceptionType, _ReturnType],
]:
    def decorator(
        except_fn: Callable[
            [_ExceptionType], Generator[_HandlerExceptionType, None, _ReturnType]
        ]
    ) -> _PartialExcHandler[_ExceptionType, _HandlerExceptionType, _ReturnType]:
        return _PartialExcHandler(exc_type, except_fn)

    return decorator


def eval_with_exc_handler(
    partial_fn: PartialFn[_ExceptionType, _ReturnType],
    except_fn: Callable[[_ExceptionType], _ReturnType],
) -> _ReturnType:
    try:
        exception = partial_fn.send(None)
    except StopIteration as _e:
        return _e.value

    return_value = except_fn(exception)
    partial_fn.close()

    return return_value


def with_handler(
    partial_fn: PartialFn[Exception, _ReturnType],
    except_clause: Union[
        _TotalExcHandler[_ExceptionType, _ReturnType],
        _PartialExcHandler[_ExceptionType, _HandlerExceptionType, _ReturnType],
    ],
) -> PartialFn[Exception, _ReturnType]:
    try:
        exception = partial_fn.send(None)
    except StopIteration as _e:
        return _e.value

    exc_type = except_clause.exc_type

    while True:
        try:
            # transfer control to the caller
            # receive the value if the caller decided to send a value in
            if isinstance(exception, exc_type):
                with closing(partial_fn):
                    if isinstance(except_clause, _TotalExcHandler):
                        return except_clause(exception)

                    handler = except_clause(exception)

                    try:
                        exception = handler.send(None)
                    except StopIteration as _e:
                        return _e.value

            yield exception
        except GeneratorExit as _e:
            # if the caller decided to close us, close `fn` first
            partial_fn.close()
            raise _e
        except BaseException:  # noqa: PIE786
            # if the caller decided to throw an exception
            exc_info = sys.exc_info()
            try:
                # throw the exception into `fn`
                # at this point it can yield another value
                # return a value by raising stop iteration
                # or raise exception that we should not handle
                exception = partial_fn.throw(*exc_info)
            except StopIteration as _e:
                return_value = _e.value
                break

    return return_value
