import sys
from typing import Callable, Generator, Generic, NoReturn, Type, TypeVar, Union

_ExceptionType = TypeVar("_ExceptionType", bound=Exception)
_ExceptionUnionType = TypeVar("_ExceptionUnionType", bound=Exception)
_ReturnType = TypeVar("_ReturnType")

PartialFn = Generator[_ExceptionType, None, _ReturnType]


def throw(exception: _ExceptionType) -> Generator[_ExceptionType, None, NoReturn]:
    yield exception
    # seems like `yield from` doesn't respect `NoReturn` annotation
    raise AssertionError("throw interrupts execution")


def try_eval(
    partial_fn: PartialFn[_ExceptionUnionType, _ReturnType],
) -> Union[_ExceptionUnionType, _ReturnType]:
    try:
        return next(partial_fn)
    except StopIteration as _e:
        return _e.value


class _ExceptionHandler(Generic[_ExceptionType]):
    def __init__(
        self,
        exc_type: Type[_ExceptionType],
        handler_fn: Callable[[_ExceptionType], None],
    ):
        self.exc_type = exc_type
        self.handler_fn = handler_fn

    def __call__(self, exception: _ExceptionType) -> None:
        self.handler_fn(exception)


def can_handle(
    exc_type: Type[_ExceptionType],
) -> Callable[[Callable[[_ExceptionType], None]], _ExceptionHandler[_ExceptionType]]:
    def decorator(
        handler_fn: Callable[[_ExceptionType], None]
    ) -> _ExceptionHandler[_ExceptionType]:
        return _ExceptionHandler(exc_type, handler_fn)

    return decorator


class ExceptionState(Generic[_ExceptionType]):
    pass


class HandlerInvocation(ExceptionState[_ExceptionType]):
    def __init__(
        self,
        exception: _ExceptionType,
        handler_fn: Callable[[_ExceptionType], None],
    ) -> None:
        self.exception = exception
        self.handler = handler_fn


def eval_with_handler(
    partial_fn: PartialFn[_ExceptionType, _ReturnType],
    handler_fn: Callable[[_ExceptionType], None],
) -> Union[_ReturnType, HandlerInvocation[_ExceptionType]]:
    try:
        exception = partial_fn.send(None)
    except StopIteration as _e:
        return _e.value

    handler_fn(exception)
    partial_fn.close()

    if isinstance(handler_fn, _ExceptionHandler):
        handler_fn = handler_fn.handler_fn

    return HandlerInvocation(exception, handler_fn)


def with_handler(
    partial_fn: PartialFn[Exception, _ReturnType],
    handler: _ExceptionHandler[_ExceptionType],
) -> PartialFn[Exception, Union[_ReturnType, ExceptionState]]:
    try:
        exception = partial_fn.send(None)
    except StopIteration as _e:
        return _e.value

    exc_type = handler.exc_type

    while True:
        try:
            # transfer control to the caller
            # receive the value if the caller decided to send a value in
            if isinstance(exception, exc_type):
                handler(exception)
                partial_fn.close()
                return HandlerInvocation(exception, handler.handler_fn)

            resume_value = yield exception
        except GeneratorExit as _e:
            # if the caller decided to close us, close `gtr` first
            partial_fn.close()
            raise _e
        except BaseException:  # noqa: PIE786
            # if the caller decided to throw an exception
            exc_info = sys.exc_info()
            try:
                # throw the exception into `gtr`
                # at this point it can yield another value
                # return a value by raising stop iteration
                # or raise exception that we should not handle
                exception = partial_fn.throw(*exc_info)
            except StopIteration as _e:
                return_value = _e.value
                break
        else:
            # if throw or close were not used on us
            try:
                exception = partial_fn.send(resume_value)
            except StopIteration as _e:
                return_value = _e.value
                break

    return return_value


def evaluate(
    partial_fn: Generator[None, None, _ReturnType],
) -> _ReturnType:
    try:
        next(partial_fn)
        raise AssertionError("argument doesn't yield")
    except StopIteration as _e:
        return _e.value
