import sys
from contextlib import closing
from typing import Callable, Generator, Generic, NoReturn, Type, TypeVar, Union

_ExceptionType = TypeVar("_ExceptionType", bound=Exception)
_HandlerExceptionType = TypeVar("_HandlerExceptionType", bound=Exception)
_ReturnType = TypeVar("_ReturnType")

ReturnWithFx = Generator[_ExceptionType, None, _ReturnType]


def throw(exception: _ExceptionType) -> ReturnWithFx[_ExceptionType, NoReturn]:
    yield exception
    # seems like `yield from` doesn't respect `NoReturn` annotation
    raise AssertionError("throw interrupts execution")


def try_eval(
    return_with_fx: ReturnWithFx[_ExceptionType, _ReturnType],
) -> Union[_ExceptionType, _ReturnType]:
    try:
        return next(return_with_fx)
    except StopIteration as _e:
        return _e.value


class ExcHandler(Generic[_ExceptionType, _ReturnType]):
    def __init__(
        self,
        exc_type: Type[_ExceptionType],
        handler_fn: Callable[[_ExceptionType], _ReturnType],
    ):
        self.exc_type = exc_type
        self.handler_fn = handler_fn

    def __call__(self, exception: _ExceptionType) -> _ReturnType:
        return self.handler_fn(exception)


class ExcHandlerWithFx(Generic[_ExceptionType, _HandlerExceptionType, _ReturnType]):
    def __init__(
        self,
        exc_type: Type[_ExceptionType],
        handler_fn_with_fx: Callable[
            [_ExceptionType], ReturnWithFx[_HandlerExceptionType, _ReturnType]
        ],
    ):
        self.exc_type = exc_type
        self.handler_fn_with_fx = handler_fn_with_fx

    def __call__(
        self, exception: _ExceptionType
    ) -> ReturnWithFx[_HandlerExceptionType, _ReturnType]:
        return self.handler_fn_with_fx(exception)


def exc_handler(
    exc_type: Type[_ExceptionType],
) -> Callable[
    [Callable[[_ExceptionType], _ReturnType]],
    ExcHandler[_ExceptionType, _ReturnType],
]:
    def decorator(
        except_fn: Callable[[_ExceptionType], _ReturnType]
    ) -> ExcHandler[_ExceptionType, _ReturnType]:
        return ExcHandler(exc_type, except_fn)

    return decorator


def exc_handler_with_fx(
    exc_type: Type[_ExceptionType],
) -> Callable[
    [Callable[[_ExceptionType], ReturnWithFx[_HandlerExceptionType, _ReturnType]]],
    ExcHandlerWithFx[_ExceptionType, _HandlerExceptionType, _ReturnType],
]:
    def decorator(
        except_fn: Callable[
            [_ExceptionType], ReturnWithFx[_HandlerExceptionType, _ReturnType]
        ]
    ) -> ExcHandlerWithFx[_ExceptionType, _HandlerExceptionType, _ReturnType]:
        return ExcHandlerWithFx(exc_type, except_fn)

    return decorator


def eval_with_exc_handler(
    return_with_fx: ReturnWithFx[_ExceptionType, _ReturnType],
    except_fn: Callable[[_ExceptionType], _ReturnType],
) -> _ReturnType:
    try:
        exception = return_with_fx.send(None)
    except StopIteration as _e:
        return _e.value

    return_value = except_fn(exception)
    return_with_fx.close()

    return return_value


def with_handler(
    return_with_fx: ReturnWithFx[Exception, _ReturnType],
    except_clause: Union[
        ExcHandler[_ExceptionType, _ReturnType],
        ExcHandlerWithFx[_ExceptionType, _HandlerExceptionType, _ReturnType],
    ],
) -> ReturnWithFx[Exception, _ReturnType]:
    try:
        exception = return_with_fx.send(None)
    except StopIteration as _e:
        return _e.value

    exc_type = except_clause.exc_type

    while True:
        try:
            # transfer control to the caller
            # receive the value if the caller decided to send a value in
            if isinstance(exception, exc_type):
                with closing(return_with_fx):
                    if isinstance(except_clause, ExcHandler):
                        return except_clause(exception)

                    handler = except_clause(exception)

                    try:
                        exception = handler.send(None)
                    except StopIteration as _e:
                        return _e.value

            yield exception
        except GeneratorExit as _e:
            # if the caller decided to close us, close `fn` first
            return_with_fx.close()
            raise _e
        except BaseException:  # noqa: PIE786
            # if the caller decided to throw an exception
            exc_info = sys.exc_info()
            try:
                # throw the exception into `fn`
                # at this point it can yield another value
                # return a value by raising stop iteration
                # or raise exception that we should not handle
                exception = return_with_fx.throw(*exc_info)
            except StopIteration as _e:
                return_value = _e.value
                break

    return return_value
