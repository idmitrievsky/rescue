from contextlib import suppress
from typing import Any, Callable, ClassVar, Generator, Generic, Type, TypeVar

_ResumeType = TypeVar("_ResumeType")
T = TypeVar("T")


class Effect(Generic[_ResumeType]):
    resume_with: ClassVar[Type[_ResumeType]]

    def perform(self: T) -> Generator[T, _ResumeType, _ResumeType]:
        resume_with = yield self
        return resume_with  # noqa: PIE781


_EffectType = TypeVar("_EffectType", bound=Effect[Any])
_ReturnType = TypeVar("_ReturnType")


# ImpureFn = Generator[_EffectType, Any, _ReturnType]


# class _EffectHandler(Generic[_EffectType, _ResumeType]):
#     def __init__(
#         self,
#         effect_type: Type[_EffectType],
#         resume_type: Type[_ResumeType],
#         handler_fn: Callable[[_EffectType], Generator[_ResumeType, None, None]],
#     ):
#         self.effect_type = effect_type
#         self.resume_with = resume_type
#         self.handler_fn = handler_fn
#
#     def __call__(self, effect: _EffectType) -> Generator[_ResumeType, None, None]:
#         return self.handler_fn(effect)


# def can_handle(
#     effect_type: Type[_EffectType],
#     resume_with: Type[_ResumeType],
# ) -> Callable[
#     [Callable[[_EffectType], Generator[_ResumeType, None, None]]],
#     _EffectHandler[_EffectType, _ResumeType],
# ]:
#     def decorator(
#         handler_fn: Callable[[_EffectType], Generator[_ResumeType, None, None]]
#     ) -> _EffectHandler[_EffectType, _ResumeType]:
#         return _EffectHandler(effect_type, resume_with, handler_fn)
#
#     return decorator


def eval_with_handler(
    impure_fn: Generator[_EffectType, _ResumeType, _ReturnType],
    handler: Callable[[_EffectType], Generator[_ResumeType, None, None]],
) -> _ReturnType:
    try:
        effect = next(impure_fn)
    except StopIteration as _e:
        return _e.value

    stack = []

    while True:
        h = handler(effect)
        stack.append(h)
        resume_value = next(h)
        try:
            effect = impure_fn.send(resume_value)
        except StopIteration as _e:
            return_value = _e.value
            break

    for h in reversed(stack):
        with suppress(StopIteration):
            next(h)
    return return_value
