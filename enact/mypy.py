from typing import Callable, Optional, Type

from mypy.plugin import FunctionContext, Plugin
from mypy.types import CallableType, NoneType, Type as TypeType, UnionType


def function_callback(ctx: FunctionContext) -> TypeType:
    partial_fn_exc_type = ctx.arg_types[0][0].args[0]  # type: ignore
    partial_fn_exc_type_seq = (
        frozenset(partial_fn_exc_type.items)
        if isinstance(partial_fn_exc_type, UnionType)
        else frozenset((partial_fn_exc_type,))
    )
    handler_type = ctx.arg_types[1][0]

    if isinstance(handler_type, CallableType):
        handler_exc_type = ctx.arg_types[1][0].arg_types[0]  # type: ignore
    else:
        handler_exc_type = ctx.arg_types[1][0].args[0]  # type: ignore

    handler_exc_type_seq = (
        frozenset(handler_exc_type.items)
        if isinstance(handler_exc_type, UnionType)
        else frozenset((handler_exc_type,))
    )
    exc_type_seq = partial_fn_exc_type_seq - handler_exc_type_seq

    exc_type = UnionType(tuple(exc_type_seq)) if exc_type_seq else NoneType()

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
