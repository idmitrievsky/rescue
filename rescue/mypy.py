from typing import Callable, FrozenSet, Optional, Type, Union

from mypy.plugin import FunctionContext, Plugin
from mypy.types import Instance, NoneType, Type as TypeType, UnionType


def _frozen_set_from_type(exc_type: Union[TypeType, UnionType]) -> FrozenSet[TypeType]:
    return (
        frozenset(exc_type.items)
        if isinstance(exc_type, UnionType)
        else frozenset((exc_type,))
    )


def function_callback(ctx: FunctionContext) -> TypeType:
    thunk_exc_type = ctx.arg_types[0][0].args[0]  # type: ignore
    thunk_exc_type_set = _frozen_set_from_type(thunk_exc_type)

    handler_type = ctx.arg_types[1][0]

    if (
        isinstance(handler_type, Instance)
        and handler_type.type.fullname == "rescue.core.ExcHandler"
    ):
        drop_exc_type = handler_type.args[0]
        handler_exc_type = _frozen_set_from_type(handler_type.args[1])
    else:
        raise AssertionError("handler is an instance of ExcHandler")

    drop_exc_type_set = _frozen_set_from_type(drop_exc_type)

    exc_type_set = (thunk_exc_type_set - drop_exc_type_set) | handler_exc_type

    exc_type_set = exc_type_set - {NoneType()}

    exc_type = UnionType(tuple(exc_type_set)) if exc_type_set else NoneType()

    return_type = ctx.arg_types[0][0].args[2]  # type: ignore
    if return_type is None:
        return_type = NoneType()

    return ctx.api.named_generic_type(
        "typing.Generator",
        [
            exc_type,
            NoneType(),
            return_type,
        ],
    )


class CustomPlugin(Plugin):
    def get_function_hook(
        self, fullname: str
    ) -> Optional[Callable[[FunctionContext], TypeType]]:
        if fullname == "rescue.core.bind":
            return function_callback
        return None


def plugin(_: str) -> Type[Plugin]:
    return CustomPlugin
