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


class _ExceptClause(Generic[_ExceptionType]):
    def __init__(
        self,
        exc_type: Type[_ExceptionType],
        except_fn: Callable[[_ExceptionType], None],
    ):
        self.exc_type = exc_type
        self.except_fn = except_fn

    def __call__(self, exception: _ExceptionType) -> None:
        self.except_fn(exception)


def can_except(
    exc_type: Type[_ExceptionType],
) -> Callable[[Callable[[_ExceptionType], None]], _ExceptClause[_ExceptionType]]:
    def decorator(
        except_fn: Callable[[_ExceptionType], None]
    ) -> _ExceptClause[_ExceptionType]:
        return _ExceptClause(exc_type, except_fn)

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


def eval_with_except(
    partial_fn: PartialFn[_ExceptionType, _ReturnType],
    except_fn: Callable[[_ExceptionType], None],
) -> Union[_ReturnType, HandlerInvocation[_ExceptionType]]:
    try:
        exception = partial_fn.send(None)
    except StopIteration as _e:
        return _e.value

    except_fn(exception)
    partial_fn.close()

    if isinstance(except_fn, _ExceptClause):
        except_fn = except_fn.except_fn

    return HandlerInvocation(exception, except_fn)


def with_handler(
    partial_fn: PartialFn[Exception, _ReturnType],
    except_clause: _ExceptClause[_ExceptionType],
) -> PartialFn[Exception, Union[_ReturnType, ExceptionState]]:
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
                except_clause(exception)
                partial_fn.close()
                return HandlerInvocation(exception, except_clause.except_fn)

            resume_value = yield exception
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
        else:
            # if throw or close were not used on us
            try:
                exception = partial_fn.send(resume_value)
            except StopIteration as _e:
                return_value = _e.value
                break

    return return_value
