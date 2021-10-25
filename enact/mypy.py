from typing import Callable, FrozenSet, Optional, Type, Union

from mypy.plugin import FunctionContext, Plugin
from mypy.types import CallableType, Instance, NoneType, Type as TypeType, UnionType


def _frozen_set_from_type(exc_type: Union[TypeType, UnionType]) -> FrozenSet[TypeType]:
    return (
        frozenset(exc_type.items)
        if isinstance(exc_type, UnionType)
        else frozenset((exc_type,))
    )


def function_callback(ctx: FunctionContext) -> TypeType:
    partial_fn_exc_type = ctx.arg_types[0][0].args[0]  # type: ignore
    partial_fn_exc_type_set = _frozen_set_from_type(partial_fn_exc_type)

    partial_handler_exc_type: FrozenSet[TypeType] = frozenset()

    handler_type = ctx.arg_types[1][0]

    if isinstance(handler_type, CallableType):
        drop_exc_type = handler_type.arg_types[0]
    elif isinstance(handler_type, Instance):
        drop_exc_type = handler_type.args[0]

        if handler_type.type.fullname == "enact.exc.ExcHandlerWithFx":
            partial_handler_exc_type = _frozen_set_from_type(handler_type.args[1])
    else:
        raise AssertionError(
            "handler is either a callable or an instance of ExcHandler"
        )

    drop_exc_type_set = _frozen_set_from_type(drop_exc_type)

    exc_type_set = (
        partial_fn_exc_type_set - drop_exc_type_set
    ) | partial_handler_exc_type

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
        if fullname.endswith("with_handler"):
            return function_callback
        return None


def plugin(_: str) -> Type[Plugin]:
    return CustomPlugin
