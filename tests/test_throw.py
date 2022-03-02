from typing import Generator

import pytest

from rescue.core import throw


def always_throw() -> Generator[RuntimeError, None, int]:
    yield from throw(RuntimeError("not ok"))
    return 0


def test_throw_can_yield_once() -> None:
    gtr = always_throw()
    exc = next(gtr)
    assert isinstance(exc, RuntimeError)


def test_throw_can_yield_only_once() -> None:
    gtr = always_throw()
    next(gtr)
    with pytest.raises(AssertionError, match="throw interrupts execution"):
        next(gtr)
